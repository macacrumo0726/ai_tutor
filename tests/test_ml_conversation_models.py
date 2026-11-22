from ai_tutor.conversation.ml_models import CentroidClassifier, default_intent_classifier


def test_centroid_classifier_trains_and_returns_scores():
    model = CentroidClassifier().fit({
        "choice": ["dime tú", "elige por mí"],
        "uncertain": ["mmm", "no estoy seguro"],
    })
    prediction = model.predict("dime tú qué hacemos")
    assert prediction.label == "choice"
    assert 0.0 <= prediction.confidence <= 1.0
    assert set(prediction.scores) == {"choice", "uncertain"}


def test_default_intent_model_handles_paraphrases_without_llm():
    model = default_intent_classifier()
    assert model.predict("decide tú el siguiente ejercicio").label in {"choose_for_student", "exercise_request"}
    assert model.predict("no sé si está bien").label == "feedback_uncertain"

