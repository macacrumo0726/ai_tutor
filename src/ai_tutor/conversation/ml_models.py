"""Small, deterministic ML models used before retrieval.

The models are centroid classifiers over the existing hashing encoder.  They
are intentionally dependency-free and train in milliseconds, which makes them
appropriate for the local pilot and for an Azure deployment without a second
model server.  They can later be replaced by a fine-tuned MiniLM/XLM-R model
behind the same interface.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from ai_tutor.embeddings.encoder import HashingEncoder


@dataclass(frozen=True)
class Prediction:
    label: str
    confidence: float
    scores: dict[str, float]


class CentroidClassifier:
    """Multiclass nearest-centroid classifier with calibrated margin score."""

    def __init__(self, encoder: HashingEncoder | None = None):
        self.encoder = encoder or HashingEncoder(dimensions=512)
        self.centroids: dict[str, np.ndarray] = {}

    def fit(self, samples: dict[str, list[str]]) -> "CentroidClassifier":
        for label, texts in samples.items():
            vectors = self.encoder.encode(texts)
            centroid = vectors.mean(axis=0)
            norm = np.linalg.norm(centroid) or 1.0
            self.centroids[label] = centroid / norm
        return self

    def predict(self, text: str) -> Prediction:
        if not self.centroids:
            return Prediction("unknown", 0.0, {})
        vector = self.encoder.encode([text])[0]
        scores = {label: float(vector @ centroid) for label, centroid in self.centroids.items()}
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best, second = ranked[0], ranked[1][1] if len(ranked) > 1 else -1.0
        # Margin is deliberately conservative: uncertain turns fall through
        # to the state-aware deterministic controller.
        confidence = max(0.0, min(1.0, (best[1] - second + 1.0) / 2.0))
        return Prediction(best[0], confidence, scores)


INTENT_EXAMPLES = {
    "choose_for_student": [
        "dime tú qué hacemos", "elige por mí", "decide tú", "escoge el ejercicio",
        "propón una práctica", "lo que prefieras", "como quieras",
    ],
    "feedback_check": [
        "estuvo bien mi respuesta", "lo hice correctamente", "respondí bien",
        "mi solución es correcta", "puedes revisar mi respuesta",
    ],
    "feedback_uncertain": [
        "mmm", "hmm", "no estoy seguro", "tengo dudas", "me quedé pensando",
        "creo que no", "no sé si está bien",
    ],
    "exercise_request": [
        "quiero practicar", "dame un ejercicio", "propón un problema",
        "quiero hacer un ejemplo", "ponme una práctica",
    ],
    "topic_switch": [
        "cambiemos de tema", "ahora quiero estudiar otra cosa", "pasemos a otro concepto",
    ],
}


def default_intent_classifier() -> CentroidClassifier:
    return CentroidClassifier().fit(INTENT_EXAMPLES)


RESPONSE_TYPE_EXAMPLES = {
    "example_submission": [
        "¿Tienes un ejemplo específico?", "escribe una función concreta",
        "comparte la expresión concreta", "dame el enunciado completo",
    ],
    "student_choice": [
        "¿Quieres empezar por la explicación o por un ejercicio?",
        "¿Qué parte te gustaría practicar primero?", "¿Prefieres un ejemplo?",
    ],
    "conceptual_answer": [
        "¿Qué valor obtienes?", "¿Qué regla usarías?", "¿Cuál es la respuesta?",
    ],
}

NEXT_ACTION_EXAMPLES = {
    "provide_scaffold": ["el estudiante no está seguro", "respuesta incorrecta", "necesita una pista"],
    "check_attempt": ["el estudiante dio un ejercicio", "verifica la respuesta", "revisa el procedimiento"],
    "offer_exercise": ["propón una práctica", "ya entendió el concepto", "hacer un ejercicio"],
    "activate_prerequisite": ["falta el prerrequisito", "repasar operaciones previas", "conocimiento previo débil"],
}


def default_response_type_classifier() -> CentroidClassifier:
    return CentroidClassifier().fit(RESPONSE_TYPE_EXAMPLES)


def default_next_action_classifier() -> CentroidClassifier:
    return CentroidClassifier().fit(NEXT_ACTION_EXAMPLES)
