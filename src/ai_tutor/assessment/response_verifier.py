from __future__ import annotations

import re
from typing import Optional


NUMBER = r"[-+]?\d+(?:[.,]\d+)?"


def _number(text: str) -> Optional[float]:
    match = re.fullmatch(
        rf"\s*(?:x\s*=\s*|ser[ií]a\s+)?({NUMBER})\s*[.!?]*\s*",
        text or "",
        re.IGNORECASE,
    )
    return float(match.group(1).replace(",", ".")) if match else None


def verify_short_math_response(message: str, previous_tutor_message: str):
    """Verify narrow, auditable micro-checks before an LLM can praise them.

    Version 1 intentionally handles only the linear-denominator pattern. An
    unsupported question remains unscored rather than being guessed.
    """
    student_value = _number(message)
    if student_value is None or not previous_tutor_message:
        return None

    normalized = previous_tutor_message.replace("−", "-").replace("–", "-")
    asks_denominator = bool(re.search(
        r"denominador|no\s+puede\s+tomar|divisi[oó]n\s+entre\s+cero",
        normalized,
        re.IGNORECASE,
    ))
    if not asks_denominator:
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
    }
