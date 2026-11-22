import pytest

from ai_tutor.assessment.bank import build_micro_check
from ai_tutor.assessment.policy import decide
from ai_tutor.assessment.schema import AssessmentResult
from ai_tutor.assessment.service import AssessmentService
from ai_tutor.assessment.validators import evaluate
from ai_tutor.memory import AuthenticationService, ConversationRepository, LearningProfileService


def test_numeric_micro_check_accepts_equivalent_answer():
    check=build_micro_check("2_1_dominio_de_una_funcion","Dominio de una función")
    result=evaluate(check,"x = 3")
    assert result.correct and result.score==1.0


def test_numeric_validator_rejects_unsafe_or_wrong_expression():
    check=build_micro_check("2_1_dominio_de_una_funcion","Dominio")
    assert not evaluate(check,"4").correct
    assert not evaluate(check,"__import__('os')").correct


def test_policy_moves_from_hint_to_prerequisite():
    wrong=AssessmentResult(False,0.0,"4","incorrecta","numeric_equivalence")
    assert decide(wrong,.4,1,["algebra"]).action=="hint"
    decision=decide(wrong,.4,3,["algebra"])
    assert decision.action=="remediate_prerequisite" and decision.next_concept_id=="algebra"


def test_assessment_persists_attempt_and_updates_mastery(tmp_path):
    repository=ConversationRepository(tmp_path/"assessment.sqlite3")
    auth=AuthenticationService(repository); auth.register("student","Student","1234")
    learning=LearningProfileService(repository)
    service=AssessmentService(repository,learning,{"domain":"Dominio"},{"domain":["algebra"]})
    conversation=repository.create_conversation("student")
    check=service.create(["domain"])
    result=service.submit("student",conversation.conversation_id,check.to_dict(),"3")
    assert result["evaluation"]["correct"] is True
    assert result["mastery_after"] > result["mastery_before"]
    assert len(repository.list_assessment_attempts("student"))==1


def test_keyword_fallback_supports_partial_score():
    check=build_micro_check("custom_concept","Transformación algebraica")
    result=evaluate(check,"La transformación aplica una operación algebraica")
    assert 0 < result.score <= 1


def test_matrix_numeric_micro_check_is_verified_against_latest_tutor_question():
    from ai_tutor.assessment.response_verifier import verify_short_math_response

    tutor_question = (
        "Si tuviéramos una matriz con el número 4 en la esquina superior izquierda "
        "y otra con el número 3 en esa misma posición, ¿qué número iría en esa esquina del resultado?"
    )
    result = verify_short_math_response("7", tutor_question)
    assert result["kind"] == "numeric_addition_v1"
    assert result["status"] == "correct"
    assert result["expected_value"] == 7


def test_function_rule_yes_no_answer_is_verified_from_previous_question():
    from ai_tutor.assessment.response_verifier import verify_short_math_response

    tutor_question = (
        "Si al poner una entrada obtienes dos valores diferentes de salida, "
        "¿crees que esa ecuación cumpliría la regla para ser una función?"
    )
    result = verify_short_math_response("no", tutor_question)
    assert result["kind"] == "binary_function_rule_v1"
    assert result["status"] == "correct"
