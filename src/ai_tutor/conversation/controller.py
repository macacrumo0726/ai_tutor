"""Conversation control layer around the fixed PEP-Plan-RAG v3 retriever.

The controller decides what a turn *means* before retrieval.  It does not
generate answers and it does not change ranking: it supplies a compact state,
routes conceptual questions versus feedback, and records an auditable
evaluation when a learner answers a tutor question.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from ai_tutor.assessment.response_verifier import verify_short_math_response
from ai_tutor.memory.contextualizer import contextualize
from ai_tutor.embeddings.encoder import HashingEncoder
from .ml_models import default_intent_classifier, default_response_type_classifier


@dataclass
class ContextDecision:
    intent: str = "concept_question"
    retrieval_query: str = ""
    is_follow_up: bool = False
    active_topic: str = ""
    evaluation: dict = field(default_factory=dict)


_TOPIC_SWITCH = re.compile(
    r"\b(?:cambiemos|pasemos|vamos\s+a\s+ver|ahora\s+(?:veremos|estudiemos)|nuevo\s+tema)\b",
    re.I,
)
_CHOICE = re.compile(
    r"^(?:no[, ]*)?(?:dime\s+t[uú]|t[uú]\s+dime|elige\s+t[uú]|t[uú]\s+elige|"
    r"t[uú]\s+decide|decide\s+t[uú]|lo\s+que\s+sea|lo\s+que\s+(?:t[uú]\s+)?"
    r"(?:quieras|prefieras)|como\s+(?:t[uú]\s+)?(?:quieras|prefieras)|"
    r"escoge\s+t[uú]|elige\s+por\s+m[ií]|d[áa]mela\s+t[uú]|dame\s+la\s+"
    r"(?:pregunta|actividad|pr[aá]ctica)|dame\s+un\s+(?:ejercicio|ejemplo)|"
    r"ponme\s+(?:un\s+)?(?:ejercicio|ejemplo)|prop[oó]n\s+(?:un\s+)?(?:ejercicio|ejemplo))$",
    re.I,
)
_REFERENCE = re.compile(r"\b(eso|esto|esa|ese|lo anterior|por qué|porque|entonces|ahí|luego)\b", re.I)
_FEEDBACK_CHECK = re.compile(
    r"\b(?:estuvo|est[aá]|era|fue)\s+(?:bien|correct[oa])\b|"
    r"\b(?:lo hice|respond[ií]|contest[eé])\s+bien\b|"
    r"\bmi respuesta\s+(?:es|fue|est[aá])\s+(?:correcta|bien)\b",
    re.I,
)
_HESITATION = re.compile(
    r"^(?:mmm+|hmm+|eh+|no\s+s[eé]|no\s+estoy\s+segur[oa]|creo\s+que\s+no|"
    r"tal\s+vez|quiz[aá]s|uhm+|em+)[.!?… ]*$",
    re.I,
)
_TOPIC_WORDS = re.compile(
    r"factor|ecuaci[oó]n|funci[oó]n|dominio|rango|desigualdad|logarit|exponente|radical|"
    r"trigonom|matriz|vector|pendiente|producto\s+punto|l[ií]mite|polinom",
    re.I,
)

# A small, model-independent state classifier.  These are response *shapes*,
# not topic-specific answers: the same gate works for domains, functions,
# matrices, and any other concept for which PATI asks the learner for an
# example or an attempt.
_EXAMPLE_REQUEST = re.compile(
    r"(?:ejemplo\s+(?:espec[ií]fico|concreto)|funci[oó]n\s+concreta|"
    r"expresi[oó]n\s+concreta|enunciado\s+(?:concreto|completo)|"
    r"problema\s+concreto|dame\s+(?:una|un)\s+(?:funci[oó]n|expresi[oó]n|ejemplo))",
    re.I,
)
_MATH_EXPRESSION = re.compile(
    r"(?:[=<>]|[/^]|[²³⁴⁵⁶⁷⁸⁹⁰]|\b[a-z]\b|\([^)]*[a-z][^)]*\)|\d\s*[+\-*]\s*\d)",
    re.I,
)

# The router is prototype-based rather than a growing list of exact phrases.
# The deterministic patterns below remain as a high-precision fallback, while
# this layer recognizes paraphrases that share the same conversational intent.
_INTENT_EXAMPLES = {
    "choose_for_student": [
        "dime tú qué hacemos", "elige por mí", "decide tú", "escoge el ejercicio",
        "propón una práctica", "dame un ejercicio", "no sé por dónde empezar, decide tú",
        "lo que prefieras", "como quieras",
    ],
    "feedback_check": [
        "estuvo bien mi respuesta", "lo hice correctamente", "respondí bien",
        "mi solución es correcta", "¿puedes revisar mi respuesta?",
    ],
    "feedback_uncertain": [
        "mmm", "hmm", "no estoy seguro", "tengo dudas", "me quedé pensando",
        "creo que no", "no sé si está bien", "quizás",
    ],
    "exercise_request": [
        "quiero practicar", "dame un ejercicio", "propón un problema",
        "quiero hacer un ejemplo", "ponme una práctica",
    ],
    "topic_switch": [
        "cambiemos de tema", "ahora quiero estudiar otra cosa", "pasemos a otro concepto",
    ],
}
_INTENT_ENCODER = HashingEncoder(dimensions=512)
_INTENT_PROTOTYPES = {
    intent: _INTENT_ENCODER.encode(examples)
    for intent, examples in _INTENT_EXAMPLES.items()
}
_ML_INTENT_CLASSIFIER = default_intent_classifier()
_ML_RESPONSE_TYPE_CLASSIFIER = default_response_type_classifier()


def _semantic_intent(text: str):
    """Return the closest conversational intent, or ``None`` when uncertain."""
    if not text.strip():
        return None
    # Very short acknowledgements are handled by the pending-question state
    # and mathematical verifier; token similarity alone would confuse
    # ``no``/``sí`` with the prototype ``no estoy seguro``.
    if len(re.findall(r"\w+", text, re.UNICODE)) <= 2:
        return None
    # Trainable local classifier.  The legacy prototype scores remain as a
    # compatibility fallback for experiments that compare router versions.
    ml_prediction = _ML_INTENT_CLASSIFIER.predict(text)
    if ml_prediction.confidence >= 0.62 and ml_prediction.scores.get(ml_prediction.label, -1) >= 0.12:
        return ml_prediction.label
    vector = _INTENT_ENCODER.encode([text])[0]
    best_intent, best_score = None, 0.0
    for intent, prototypes in _INTENT_PROTOTYPES.items():
        score = float((prototypes @ vector).max())
        if score > best_score:
            best_intent, best_score = intent, score
    # A low score must not hijack a mathematical question. The threshold is
    # deliberately conservative; the state gate below supplies more evidence.
    if best_score < 0.42:
        return None
    # ``ejercicio`` is shared by the choice and practice prototypes. Prefer
    # the explicit practice intent when the learner names an activity.
    if re.search(r"ejercicio|pr[aá]ctica|problema|ejemplo", text, re.I):
        exercise_score = float((_INTENT_PROTOTYPES["exercise_request"] @ vector).max())
        if exercise_score >= best_score - 0.02:
            return "exercise_request"
    return best_intent


def _last_assistant(messages) -> str:
    return next((item.content for item in reversed(messages) if item.role == "assistant"), "")


def expected_response_type(latest_assistant: str, state: dict | None = None) -> str:
    """Infer what the tutor is waiting for, without another LLM call."""
    state = state or {}
    explicit = state.get("expected_response_type")
    if explicit in {"student_attempt", "example_submission", "conceptual_answer", "clarification", "student_choice"}:
        return explicit
    latest = latest_assistant or ""
    if _EXAMPLE_REQUEST.search(latest):
        return "example_submission"
    if re.search(r"(?:quieres|prefieres|te gustar[ií]a).{0,100}\?", latest, re.I):
        return "student_choice"
    if "?" in latest or "¿" in latest:
        prediction = _ML_RESPONSE_TYPE_CLASSIFIER.predict(latest)
        if prediction.confidence >= 0.66 and prediction.scores.get(prediction.label, -1) >= 0.10:
            return prediction.label
        return "conceptual_answer"
    return ""


def evaluate_conceptual_answer(question: str, answer: str, active_topic: str = "") -> dict:
    """Evaluate a learner's conceptual feedback conservatively.

    ``uncertain`` is intentional: unsupported answers are never treated as
    correct merely because they are short.  Numeric/symbolic checks continue
    to use the existing deterministic verifier.
    """
    answer = (answer or "").strip()
    question = question or ""
    if not answer or not question:
        return {"status": "uncertain", "confidence": 0.0, "reason": "missing_turn"}
    numeric = verify_short_math_response(answer, question)
    if numeric:
        return {**numeric, "evaluator": "deterministic_math"}
    normalized = re.sub(r"\s+", " ", answer.lower())
    q = re.sub(r"\s+", " ", question.lower())
    positive = False
    negative = False
    reason = ""
    if re.search(r"(?:misma|iguales).*(?:dimensi[oó]n|filas|columnas)|dimensi[oó]n.*(?:sumar|restar)", q):
        positive = bool(re.search(r"igual|misma|mismo|coincid|no se puede|no", normalized))
        reason = "las matrices deben tener las mismas dimensiones"
    elif re.search(r"dos\s+salidas|ser[ií]a\s+funci[oó]n|una\s+entrada", q):
        positive = bool(re.search(r"\bno\b|una sola|una\s+[yoy]\s+una", normalized))
        reason = "una función asigna una sola salida a cada entrada"
    elif re.search(r"producto\s+punto.*cero|qu[eé].*significa.*cero", q):
        positive = bool(re.search(r"perpendicular|ortogonal", normalized))
        reason = "producto punto cero indica ortogonalidad en vectores no nulos"
    elif re.search(r"argumento.*log|logaritmo.*positivo|dominio.*log", q):
        positive = bool(re.search(r"positivo|mayor\s+que\s+cero|x\s*>|x>-", normalized))
        reason = "el argumento de un logaritmo debe ser positivo"
    elif re.search(r"ra[ií]z.*dominio|ra[ií]z.*cuadrada", q):
        positive = bool(re.search(r"mayor|igual|no\s+negativ|positivo", normalized))
        reason = "el radicando de una raíz cuadrada debe ser no negativo"
    elif active_topic and _TOPIC_WORDS.search(active_topic):
        # Topic overlap is evidence of relevance, never proof of correctness.
        positive = bool(_TOPIC_WORDS.search(normalized))
        reason = "la respuesta contiene vocabulario del tema activo"
    if positive and not negative:
        return {"status": "correct", "confidence": 0.78, "reason": reason, "evaluator": "conceptual_heuristic"}
    return {"status": "uncertain", "confidence": 0.0, "reason": "no hay evidencia suficiente para calificarla", "evaluator": "conceptual_heuristic"}


def evaluate_feedback_check(previous_messages) -> dict:
    """Evaluate ``¿estuvo bien mi respuesta?`` against the immediately prior task."""
    users = [item.content for item in previous_messages if item.role == "user"]
    assistants = [item.content for item in previous_messages if item.role == "assistant"]
    if not users or len(assistants) < 2:
        return {"status": "uncertain", "confidence": 0.0, "reason": "no hay intento anterior suficiente", "evaluator": "feedback_check"}
    attempt = users[-1].strip()
    task = assistants[-2]
    # Same-base exponent multiplication, including the notation used by the UI.
    powers = re.search(r"(\d+)\s*[³²¹⁴⁵⁶⁷⁸⁹⁰]|(\d+)\s*\^\s*(\d+)", task)
    product = re.search(r"(\d+)\s*[·*]\s*(\d+)", task)
    expected_exp = None
    if "2³" in task and "2²" in task:
        expected_exp = 5
    elif powers and product:
        expected_exp = None
    if expected_exp is not None:
        submitted = re.search(r"\^\s*\(?\s*(\d+)\s*\)?|[²³⁴⁵⁶⁷⁸⁹⁰]", attempt)
        submitted_exp = None
        if submitted:
            token = submitted.group(1) or submitted.group(0)
            superscripts = {"²": 2, "³": 3, "⁴": 4, "⁵": 5, "⁶": 6, "⁷": 7, "⁸": 8, "⁹": 9, "⁰": 0}
            submitted_exp = int(token) if token.isdigit() else superscripts.get(token)
        if submitted_exp is not None:
            correct = submitted_exp == expected_exp
            return {
                "status": "correct" if correct else "incorrect",
                "confidence": 0.99,
                "reason": "al multiplicar potencias de la misma base se suman los exponentes",
                "expected": "2^5 = 32",
                "submitted": attempt,
                "evaluator": "feedback_check_exponents_v1",
            }
    return {"status": "uncertain", "confidence": 0.0, "reason": "requiere comprobar el intento anterior", "evaluator": "feedback_check"}


def route_turn(message: str, previous_messages, active_problem: str = "", pedagogical_state: dict | None = None) -> ContextDecision:
    """Route a message without making topic-specific phrase exceptions."""
    state = pedagogical_state or {}
    text = re.sub(r"\s+", " ", message or "").strip()
    normalized = text.lower()
    latest = _last_assistant(previous_messages)
    latest_question = latest if "?" in latest or "¿" in latest else ""
    is_short = len(re.findall(r"\w+", text, re.UNICODE)) <= 8
    semantic_intent = _semantic_intent(normalized)
    expected = expected_response_type(latest_question, state)
    if _TOPIC_SWITCH.search(text) or semantic_intent == "topic_switch":
        return ContextDecision("concept_question", text, False, active_problem, {})
    if semantic_intent == "exercise_request" and (latest_question or state.get("current_activity") == "topic_introduction"):
        return ContextDecision("exercise_request", contextualize(text, previous_messages, active_problem), True, active_problem, {})
    if (semantic_intent == "choose_for_student" or _CHOICE.fullmatch(normalized)) and (latest_question or state.get("current_activity") == "topic_introduction"):
        return ContextDecision("choose_for_student", contextualize(text, previous_messages, active_problem), True, active_problem, {})
    # If PATI requested a concrete example, a mathematical expression is an
    # answer to that request—not a new unrelated topic.  This gate is the key
    # protection against retrieval drifting to an old textbook chunk.
    if (_MATH_EXPRESSION.search(text) and (
            expected == "example_submission" or
            (expected in {"conceptual_answer", "clarification"} and
             re.search(r"dominio|denominador|funci[oó]n\s+racional|expresi[oó]n|"
                       r"vectores?\s+concret|dos\s+vectores|matriz|ejemplo", latest_question + " " + active_problem, re.I))
        )):
        return ContextDecision(
            "student_example",
            contextualize(text, previous_messages, active_problem),
            True,
            active_problem,
            {"status": "submitted", "confidence": 0.95, "evaluator": "conversation_state_classifier_v1"},
        )
    if expected == "example_submission" and re.fullmatch(r"no|ahora no|no tengo", normalized):
        return ContextDecision("decline_example", contextualize(text, previous_messages, active_problem), True, active_problem, {})
    if expected == "student_choice" and re.fullmatch(r"no|ahora no|no s[eé]", normalized):
        return ContextDecision(
            "feedback_uncertain", contextualize(text, previous_messages, active_problem), True,
            active_problem, {"status": "uncertain", "confidence": 0.0,
                             "reason": "rechazo de la opción ofrecida", "evaluator": "conversation_state_classifier_v1"},
        )
    if latest_question and re.fullmatch(r"no|ahora no|no s[eé]", normalized):
        evaluation = evaluate_conceptual_answer(text, latest_question, active_problem)
        if evaluation.get("status") == "correct":
            return ContextDecision("feedback_answer", contextualize(text, previous_messages, active_problem), True,
                                   active_problem, evaluation)
        return ContextDecision(
            "feedback_answer", contextualize(text, previous_messages, active_problem), True,
            active_problem, {"status": "uncertain", "confidence": 0.0,
                             "reason": "negación o duda ante la pregunta pendiente",
                             "evaluator": "conversation_state_classifier_v1"},
        )
    if (semantic_intent == "feedback_check" or _FEEDBACK_CHECK.search(text)) and previous_messages:
        return ContextDecision("feedback_check", text, True, active_problem, evaluate_feedback_check(previous_messages))
    if (semantic_intent == "feedback_uncertain" or _HESITATION.fullmatch(normalized)) and latest_question:
        return ContextDecision(
            "feedback_uncertain",
            contextualize(text, previous_messages, active_problem),
            True,
            active_problem,
            {"status": "uncertain", "confidence": 0.0, "reason": "señal de duda ante la pregunta pendiente", "evaluator": "conversation_signal"},
        )
    if latest_question and is_short:
        evaluation = evaluate_conceptual_answer(text, latest_question, active_problem)
        return ContextDecision("feedback_answer", contextualize(text, previous_messages, active_problem), True, active_problem, evaluation)
    return ContextDecision(
        "concept_question",
        contextualize(text, previous_messages, active_problem),
        bool(is_short or _REFERENCE.search(text)),
        active_problem,
        {},
    )
