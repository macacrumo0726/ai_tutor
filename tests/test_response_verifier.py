from ai_tutor.assessment import verify_short_math_response, verify_factorization_attempt


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


def test_symbolic_common_factor_micro_check_accepts_variable():
    prompt = "Si tuvieras la expresión y² + 3y, ¿cuál es la letra o factor que se repite?"
    result = verify_short_math_response("y", prompt)
    assert result["status"] == "correct"
    assert result["expected_symbol"] == "y"


def test_symbolic_common_factor_micro_check_rejects_wrong_variable():
    prompt = "En la expresión y² + 3y, ¿qué factor se repite en ambos términos?"
    result = verify_short_math_response("x", prompt)
    assert result["status"] == "incorrect"
    assert result["expected_symbol"] == "y"


def test_factorization_attempt_tracks_pair_not_previous_attempt():
    prompt = "Practiquemos: factoriza x² - 7x + 12. Busca dos números cuyo producto sea 12 y cuya suma sea -7."
    wrong = verify_factorization_attempt("4 y 3", prompt)
    assert wrong["status"] == "incorrect"
    assert wrong["student_pair"] == (4, 3)
    assert wrong["expected_pair"] == (-4, -3)


def test_factorization_attempt_understands_factor_expression():
    prompt = "Factoriza x² - 7x + 12 y escribe los dos factores."
    result = verify_factorization_attempt("x+4 y x+3", prompt)
    assert result["status"] == "correct"
    assert result["kind"] == "quadratic_factor_expression_v2"


def test_factorization_attempt_rejects_wrong_sign_expression():
    prompt = "Factoriza x² - 7x + 12 y escribe los dos factores."
    result = verify_factorization_attempt("(x-3)(x-4)", prompt)
    assert result["status"] == "incorrect"
    assert "+7x" in result["explanation"]
