from ai_tutor.assessment import verify_short_math_response


def test_linear_denominator_rejects_wrong_short_answer():
    prompt = (
        "Tenemos la expresión 1 entre (x - 5). "
        "¿Qué valor no puede tomar x en el denominador?"
    )
    result = verify_short_math_response("8", prompt)
    assert result["status"] == "incorrect"
    assert result["expected_value"] == 5
    assert result["student_value"] == 8


def test_linear_denominator_accepts_correct_answer_and_handles_plus():
    prompt = "Para 1/(x + 3), ¿qué valor hace cero el denominador?"
    result = verify_short_math_response("x = -3", prompt)
    assert result["status"] == "correct"
    assert result["expected_value"] == -3


def test_unsupported_micro_check_remains_unscored():
    assert verify_short_math_response("8", "¿Cuál es el rango de la función?") is None
    assert verify_short_math_response("no sé", "Para 1/(x - 5), ¿qué valor se excluye?") is None
