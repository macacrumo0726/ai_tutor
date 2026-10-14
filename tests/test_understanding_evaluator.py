from ai_tutor.assessment import UnderstandingEvaluator


def test_explicit_confusion_is_detected():
    result=UnderstandingEvaluator().evaluate(
        "No entiendo cómo encontrar el dominio",concept_ids=["domain"])
    assert result["classification"]=="not_understood"
    assert result["score"]<.25
    assert result["changes_mastery"] is True


def test_explanation_can_support_understanding():
    result=UnderstandingEvaluator().evaluate(
        "Primero igualo el denominador a cero porque esos valores se excluyen del dominio.",
        concept_ids=["domain"],concept_labels={"domain":"dominio"})
    assert result["classification"] in {"partial","understood"}
    assert result["score"]>=.60


def test_ungrounded_short_answer_is_not_graded():
    result=UnderstandingEvaluator().evaluate(
        "x es 3","¿Qué valor de x debes excluir?",["domain"],{"domain":"dominio"})
    assert result["classification"]=="unscored"
    assert result["score"] is None
    assert result["changes_mastery"] is False
