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


def verify_short_math_response(message: str, previous_tutor_message: str):
    """Verify narrow, auditable micro-checks before an LLM can praise them.

    Version 1 intentionally handles only the linear-denominator pattern. An
    unsupported question remains unscored rather than being guessed.
    """
    if not previous_tutor_message:
        return None

    normalized = previous_tutor_message.replace("−", "-").replace("–", "-")
    asks_denominator = bool(re.search(
        r"denominador|no\s+puede\s+tomar|divisi[oó]n\s+entre\s+cero",
        normalized,
        re.IGNORECASE,
    ))
    if not asks_denominator:
        # A micro-check may ask for the common variable in an expression such
        # as y² + 3y. This is a narrow symbolic check, not a general LLM grade.
        student_symbol = _symbol(message)
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
