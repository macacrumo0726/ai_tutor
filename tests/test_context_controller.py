from types import SimpleNamespace

from ai_tutor.conversation import evaluate_conceptual_answer, route_turn


def _message(role, content):
    return SimpleNamespace(role=role, content=content)


def test_router_handles_choice_without_topic_specific_exceptions():
    decision = route_turn(
        "dime tu",
        [_message("assistant", "¿Qué parte te gustaría practicar primero?")],
        "exponentes enteros",
        {"current_activity": "topic_introduction"},
    )
    assert decision.intent == "choose_for_student"
    assert decision.active_topic == "exponentes enteros"


def test_router_handles_preference_variants():
    decision = route_turn(
        "lo que tú prefieras",
        [_message("assistant", "¿Quieres empezar por la explicación o por un ejercicio?")],
        "prueba de la recta vertical",
        {},
    )
    assert decision.intent == "choose_for_student"


def test_router_handles_request_to_propose_an_exercise():
    decision = route_turn(
        "no, damela tu",
        [_message("assistant", "¿Quieres una función concreta para encontrar su dominio?")],
        "¿Cómo encuentro el dominio de una función racional?",
        {},
    )
    assert decision.intent == "choose_for_student"


def test_hesitation_keeps_pending_question():
    decision = route_turn(
        "mmm",
        [_message("assistant", "¿Quieres que comprobemos las raíces sustituyéndolas?")],
        "Ayúdame a factorizar x² - 5x + 6",
        {},
    )
    assert decision.intent == "feedback_uncertain"
    assert decision.evaluation["status"] == "uncertain"


def test_semantic_router_accepts_unseen_paraphrases():
    choose = route_turn(
        "no sé por dónde empezar, decide tú",
        [_message("assistant", "¿Qué parte quieres practicar?")],
        "funciones",
        {},
    )
    uncertain = route_turn(
        "me quedé pensando",
        [_message("assistant", "¿Cuál sería el dominio?")],
        "dominio",
        {},
    )
    assert choose.intent == "choose_for_student"
    assert uncertain.intent == "feedback_uncertain"


def test_router_detects_feedback_and_keeps_active_problem():
    decision = route_turn(
        "no",
        [_message("assistant", "Si una entrada tiene dos salidas, ¿sería una función?")],
        "relación y función",
        {},
    )
    assert decision.intent == "feedback_answer"
    assert decision.is_follow_up
    assert decision.evaluation["status"] == "correct"


def test_conceptual_evaluator_is_conservative_for_unknown_answer():
    result = evaluate_conceptual_answer(
        "¿Qué significa esta propiedad?", "no estoy seguro", "funciones"
    )
    assert result["status"] == "uncertain"


def test_feedback_check_evaluates_previous_exponent_attempt():
    decision = route_turn(
        "¿estuvo bien mi respuesta?",
        [
            _message("user", "Quiero practicar exponentes"),
            _message("assistant", "¿Quieres un ejercicio?"),
            _message("user", "ejercicio"),
            _message("assistant", "Simplifica 2³ · 2². ¿Qué resultado obtienes?"),
            _message("user", "suma 2^(6)"),
            _message("assistant", "La regla es sumar exponentes: 2³ · 2² = 2⁵ = 32."),
        ],
        "exponentes enteros",
        {},
    )
    assert decision.intent == "feedback_check"
    assert decision.evaluation["status"] == "incorrect"
