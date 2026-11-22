from __future__ import annotations

import re
from typing import Optional


NUMBER = r"[-+]?\d+(?:[.,]\d+)?"
SYMBOL = r"[a-zA-Z]"


def _number(text: str) -> Optional[float]:
    match = re.fullmatch(
        rf"\s*(?:x\s*=\s*|ser[ií]a\s+)?({NUMBER})\s*[.!?]*\s*",
        text or "",
        re.IGNORECASE,
    )
    return float(match.group(1).replace(",", ".")) if match else None


def _symbol(text: str) -> Optional[str]:
    match = re.fullmatch(rf"\s*(?:factor\s+|letra\s+)?({SYMBOL})\s*[.!?]*\s*", text or "", re.IGNORECASE)
    return match.group(1).lower() if match else None


def _factor_pair(text: str):
    match = re.fullmatch(r"\s*(-?\d+)\s*(?:y|,|e)\s*(-?\d+)\s*[.!?]*\s*", text or "", re.IGNORECASE)
    return (int(match.group(1)), int(match.group(2))) if match else None


def _quadratic_coefficients(text: str):
    """Extract b,c from a monic quadratic x² + b x + c."""
    normalized = (text or "").replace("−", "-").replace("–", "-").replace("²", "^2")
    match = re.search(
        r"x\s*\^\s*2\s*([+-])\s*(\d+)\s*x\s*([+-])\s*(\d+)",
        normalized, re.IGNORECASE,
    )
    if not match:
        return None
    b = int(match.group(2)) * (-1 if match.group(1) == "-" else 1)
    c = int(match.group(4)) * (-1 if match.group(3) == "-" else 1)
    return b, c


def _factor_expression_pair(text: str):
    """Read factors such as ``x+4 y x+3`` or ``(x-3)(x-4)``.

    The returned values are the roots represented by (x-r), so x+4 maps to
    -4.  This makes comparison with the required sum/product independent of
    how the learner writes the factors.
    """
    normalized = (text or "").replace("−", "-").replace("–", "-")
    matches = re.findall(r"x\s*([+-])\s*(\d+)", normalized, re.IGNORECASE)
    if len(matches) < 2:
        return None
    roots = []
    for sign, value in matches[:2]:
        number = int(value)
        roots.append(-number if sign == "+" else number)
    return tuple(roots)


def verify_factorization_attempt(message: str, previous_tutor_message: str):
    """Check a student's factor/pair attempt against the active quadratic.

    This is deliberately deterministic: it prevents a fluent generator from
    accepting an invalid pair or answering as if the learner had supplied a
    different pair.  Unsupported text returns ``None`` and remains available
    to the conversational model.
    """
    coefficients = _quadratic_coefficients(previous_tutor_message)
    if not coefficients or not re.search(r"factor|producto|suma|n[uú]meros|binomio", previous_tutor_message or "", re.I):
        return None
    b, c = coefficients
    pair = _factor_pair(message)
    factor_pair = _factor_expression_pair(message) if pair is None else None
    candidate = pair or factor_pair
    if candidate is None:
        return None
    expected = next(
        ((a, c // a) for a in range(-abs(c), abs(c) + 1)
         if a and c % a == 0 and a + c // a == b),
        None,
    )
    if expected is None:
        return None
    candidate_set, expected_set = set(candidate), set(expected)
    correct = candidate_set == expected_set
    candidate_sum, candidate_product = sum(candidate), candidate[0] * candidate[1]
    kind = "quadratic_factor_expression_v2" if factor_pair is not None else "quadratic_factor_pair_v2"
    if correct:
        explanation = f"La suma es {b} y el producto es {c}."
    elif factor_pair is not None:
        explanation = (
            f"Los factores escritos representan raíces {candidate[0]} y {candidate[1]}, "
            f"por lo que desarrollan x² {candidate_sum:+d}x {candidate_product:+d}; "
            f"se necesita x² {b:+d}x {c:+d}."
        )
    else:
        explanation = (
            f"El intento suma {candidate_sum} y multiplica {candidate_product}; "
            f"se necesita sumar {b} y multiplicar {c}."
        )
    return {
        "status": "correct" if correct else "incorrect",
        "student_pair": tuple(candidate),
        "expected_pair": tuple(expected),
        "target_coefficients": {"b": b, "c": c},
        "candidate_sum": candidate_sum,
        "candidate_product": candidate_product,
        "kind": kind,
        "confidence": 0.995,
        "explanation": explanation,
    }


def _yes_no(text: str) -> Optional[bool]:
    normalized = re.sub(r"[¡!¿?.,;:]", " ", text or "").strip().lower()
    if normalized in {"sí", "si", "sí es", "si es", "correcto"}:
        return True
    if normalized in {"no", "no es", "incorrecto"}:
        return False
    return None


def verify_short_math_response(message: str, previous_tutor_message: str):
    """Verify narrow, auditable micro-checks before an LLM can praise them.

    Version 1 intentionally handles only the linear-denominator pattern. An
    unsupported question remains unscored rather than being guessed.
    """
    if not previous_tutor_message:
        return None

    normalized = previous_tutor_message.replace("−", "-").replace("–", "-")
    yes_no = _yes_no(message)
    asks_function_rule = bool(re.search(
        r"(?:ser[ií]a|cumplir[ií]a|es)\b.{0,80}(?:funci[oó]n|regla de oro)|"
        r"dos\s+valores.{0,80}funci[oó]n|una\s+entrada.{0,80}dos\s+salidas",
        normalized, re.IGNORECASE | re.DOTALL,
    ))
    if yes_no is not None and asks_function_rule:
        # The preceding question describes two outputs for one input, so the
        # correct answer to "would it be a function?" is no.
        expected = False
        return {
            "status": "correct" if yes_no == expected else "incorrect",
            "student_value": "sí" if yes_no else "no",
            "expected_value": "no",
            "kind": "binary_function_rule_v1",
            "confidence": 0.98,
            "explanation": "Una función asigna una sola salida a cada entrada; dos salidas para una entrada incumplen la definición.",
        }
    asks_denominator = bool(re.search(
        r"denominador|no\s+puede\s+tomar|divisi[oó]n\s+entre\s+cero",
        normalized,
        re.IGNORECASE,
    ))
    if not asks_denominator:
        # Matrix and arithmetic micro-checks can legitimately receive a bare
        # numeric answer. Verify the exact two operands in the tutor's latest
        # question instead of letting retrieval reinterpret the number as a
        # new topic.
        student_number = _number(message)
        matrix_addition_context = re.search(
            r"(?:n[uú]mero|valor).{0,35}(?:esquina|posici[oó]n|suma)|"
            r"(?:misma\s+(?:posici[oó]n|entrada)|qu[eé]\s+da)",
            normalized, re.IGNORECASE | re.DOTALL,
        )
        if student_number is not None and matrix_addition_context:
            operands = [float(item.replace(",", ".")) for item in re.findall(
                rf"(?<![a-zA-Z])({NUMBER})(?![a-zA-Z])", normalized, re.IGNORECASE
            )]
            if len(operands) >= 2:
                expected = operands[-2] + operands[-1]
                return {
                    "status": "correct" if abs(student_number - expected) <= 1e-9 else "incorrect",
                    "student_value": student_number, "expected_value": expected,
                    "kind": "numeric_addition_v1", "confidence": 0.99,
                    "explanation": f"Se suman los dos valores de la misma posición: {operands[-2]:g} + {operands[-1]:g} = {expected:g}.",
                }
        # A micro-check may ask for the common variable in an expression such
        # as y² + 3y. This is a narrow symbolic check, not a general LLM grade.
        student_symbol = _symbol(message)
        pair = _factor_pair(message)
        quadratic = re.search(r"x\s*(?:²|\^2)\s*([+-])\s*(\d+)\s*x\s*([+-])\s*(\d+)", normalized, re.IGNORECASE)
        if pair and quadratic and re.search(r"factor|n[uú]meros|suma|producto", normalized, re.IGNORECASE):
            b = int(quadratic.group(2)) * (-1 if quadratic.group(1) == "-" else 1)
            c = int(quadratic.group(4)) * (-1 if quadratic.group(3) == "-" else 1)
            expected = next(((a, c // a) for a in range(-abs(c), abs(c) + 1) if a and c % a == 0 and a + c // a == b), None)
            if expected:
                correct = set(pair) == set(expected)
                return {
                    "status": "correct" if correct else "incorrect",
                    "student_pair": pair, "expected_pair": expected,
                    "kind": "quadratic_factor_pair_v1", "confidence": 0.98,
                    "explanation": f"Los factores deben sumar {b} y multiplicar {c}.",
                }
        if student_symbol is None or not re.search(r"letra|factor común|factor(?: que)? se repite", normalized, re.IGNORECASE):
            return None
        expressions = re.findall(
            rf"\b({SYMBOL})\s*(?:²|\^2)?\s*[+-]\s*\d*\s*\1\b",
            normalized,
            re.IGNORECASE,
        )
        if not expressions:
            return None
        expected_symbol = expressions[-1].lower()
        return {
            "status": "correct" if student_symbol == expected_symbol else "incorrect",
            "student_symbol": student_symbol,
            "expected_symbol": expected_symbol,
            "kind": "symbolic_common_factor_v1",
            "confidence": 0.96,
            "explanation": f"La variable {expected_symbol} aparece en ambos términos y es el factor común.",
        }

    student_value = _number(message)
    if student_value is None:
        return None

    matches = list(re.finditer(
        rf"\bx\s*([+-])\s*({NUMBER})",
        normalized,
        re.IGNORECASE,
    ))
    if not matches:
        return None

    expression = matches[-1]
    constant = float(expression.group(2).replace(",", "."))
    expected = constant if expression.group(1) == "-" else -constant
    correct = abs(student_value - expected) <= 1e-9
    return {
        "status": "correct" if correct else "incorrect",
        "student_value": student_value,
        "expected_value": expected,
        "rule": "linear_denominator_zero_v1",
        "confidence": 0.99,
        "explanation": f"x {expression.group(1)} {constant:g} = 0 implica x = {expected:g}",
        "kind": "numeric_linear_denominator_v1",
    }
