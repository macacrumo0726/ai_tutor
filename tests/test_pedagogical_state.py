from ai_tutor.api.services import TutorApplicationService
from ai_tutor.memory import ConversationRepository


def _service(tmp_path):
    service = TutorApplicationService(repository=ConversationRepository(tmp_path / "state.sqlite3"))
    service.default_provider = "instructional"
    user = service.auth.register("state-student", "State Student", "1234")
    service.repository.save_protocol_acceptance(user["user_id"], service._protocol_version(), True)
    identity = service.auth.require(user)
    conversation = service.memory.create(identity["user_id"])
    return service, identity, conversation


def test_exercise_choice_is_not_routed_as_social_ack(tmp_path):
    service, identity, conversation = _service(tmp_path)
    intro = service.ask(identity, conversation.conversation_id, "Quiero repasar exponentes y radicales")
    assert "ejercicio" in intro["answer"].lower()
    exercise = service.ask(identity, conversation.conversation_id, "ejercicio")
    assert "2³" in exercise["answer"]
    saved = service.repository.get_conversation(identity["user_id"], conversation.conversation_id)
    assert saved.pedagogical_state["current_activity"] == "guided_exercise"
    assert saved.pedagogical_state["expected_response_type"] == "student_attempt"


def test_yes_continues_pending_exercise(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Quiero repasar exponentes y radicales")
    service.ask(identity, conversation.conversation_id, "ejercicio")
    result = service.ask(identity, conversation.conversation_id, "sí")
    assert "ejercicio" in result["answer"].lower()
    assert result["metadata"]["intent"] == "exercise_confirmation"


def test_progress_confirmation_closes_pending_step_instead_of_repeating(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Ayúdame a factorizar x² - 5x + 6")
    service.ask(identity, conversation.conversation_id, "no entendí")
    service.ask(identity, conversation.conversation_id, "correcto")
    service.ask(identity, conversation.conversation_id, "siguiente")
    service.ask(identity, conversation.conversation_id, "sí, me da 0 y con x=2 también da 0")
    result = service.ask(identity, conversation.conversation_id, "verificados")
    assert result["metadata"]["intent"] == "progress_confirmation"
    assert "verificado" in result["answer"].lower()
    assert "4 - 10 + 6" not in result["answer"]


def test_failed_confirmation_does_not_close_pending_step(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Ayúdame a factorizar x² - 5x + 6")
    service.ask(identity, conversation.conversation_id, "no entendí")
    service.ask(identity, conversation.conversation_id, "siguiente")
    service.ask(identity, conversation.conversation_id, "no me da 0")
    saved = service.repository.get_conversation(identity["user_id"], conversation.conversation_id)
    assert saved.pedagogical_state.get("last_step_closed") is not True


def test_request_for_another_exercise_returns_an_actual_problem(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Ayúdame a factorizar x² - 5x + 6")
    service.ask(identity, conversation.conversation_id, "verificados")
    result = service.ask(identity, conversation.conversation_id, "dame otro ejercicio")
    assert result["metadata"]["intent"] == "exercise_request"
    assert "factoriza" in result["answer"].lower()
    assert "x²" in result["answer"]


def test_affirmative_to_root_check_continues_the_requested_action(tmp_path):
    service, identity, conversation = _service(tmp_path)
    first = service.ask(identity, conversation.conversation_id, "Ayúdame a factorizar x² - 5x + 6")
    result = service.ask(identity, conversation.conversation_id, "sí")
    assert result["metadata"]["intent"] == "continue_verification"
    assert "sustitúyelo" in result["answer"].lower()
    assert "¿quieres practicar" not in result["answer"].lower()


def test_root_verification_advances_after_zero_and_yes(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Ayúdame a factorizar x² - 5x + 6")
    first = service.ask(identity, conversation.conversation_id, "sí")
    assert "x = 3" in first["answer"]
    second = service.ask(identity, conversation.conversation_id, "0")
    assert second["metadata"]["intent"] == "verification_answer"
    assert "x = 2" in second["answer"]
    third = service.ask(identity, conversation.conversation_id, "sí")
    assert third["metadata"]["intent"] == "continue_verification"
    assert "2²" in third["answer"]
    fourth = service.ask(identity, conversation.conversation_id, "0")
    assert "ambas sustituciones" in fourth["answer"].lower()


def test_no_to_follow_up_choice_closes_naturally(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Ayúdame a factorizar x² - 5x + 6")
    service.ask(identity, conversation.conversation_id, "sí")
    service.ask(identity, conversation.conversation_id, "0")
    service.ask(identity, conversation.conversation_id, "sí")
    service.ask(identity, conversation.conversation_id, "0")
    result = service.ask(identity, conversation.conversation_id, "no")
    assert result["metadata"]["intent"] == "decline_follow_up"
    assert "cerrado" in result["answer"].lower()


def test_student_can_delegate_topic_choice(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Quiero repasar exponentes enteros")
    result = service.ask(identity, conversation.conversation_id, "no, dime tú")
    assert "exponentes" in result["answer"].lower()
    assert result["metadata"]["intent"] == "choose_for_student"


def test_unaccented_dime_tu_is_a_choice_not_a_new_question(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Quiero repasar exponentes enteros")
    result = service.ask(identity, conversation.conversation_id, "dime tu")
    assert result["metadata"]["intent"] == "choose_for_student"
    assert "exponente" in result["answer"].lower()


def test_preference_variant_keeps_vertical_line_topic(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Quiero repasar la prueba de la recta vertical")
    result = service.ask(identity, conversation.conversation_id, "lo que tú prefieras")
    assert result["metadata"]["intent"] == "choose_for_student"
    assert "recta vertical" in result["answer"].lower()


def test_domain_choice_proposes_a_concrete_function(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "¿Cómo encuentro el dominio de una función racional?")
    result = service.ask(identity, conversation.conversation_id, "no, damela tu")
    assert result["metadata"]["intent"] == "choose_for_student"
    assert "f(x) = 1/(x - 4)" in result["answer"]
    assert "-2 o 2" in result["answer"]


def test_factorization_exercise_keeps_target_and_checks_attempt(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Quiero repasar factorización algebraica")
    exercise = service.ask(identity, conversation.conversation_id, "ejercicio")
    assert "x² + 5x + 6" in exercise["answer"]
    guided = service.ask(identity, conversation.conversation_id, "paso a paso")
    assert "producto" in guided["answer"].lower()
    wrong = service.ask(identity, conversation.conversation_id, "4 y 3")
    assert "suma" in wrong["answer"].lower()
    assert wrong["metadata"]["response_verification"]["status"] == "incorrect"
    factors = service.ask(identity, conversation.conversation_id, "x+2 y x+3")
    assert "factores" in factors["answer"].lower() or "intento" in factors["answer"].lower()


def test_explicit_practice_request_is_not_sent_to_stale_retrieval(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Quiero repasar ecuaciones cuadráticas")
    result = service.ask(identity, conversation.conversation_id, "Ponme una práctica corta")
    assert result["metadata"]["intent"] == "exercise_request"
    assert "ejercicio" in result["answer"].lower() or "factoriza" in result["answer"].lower()
    assert "matrices" not in result["answer"].lower()


def test_declining_optional_root_check_does_not_enter_uncertainty_loop(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Ayúdame a factorizar x² - 5x + 6")
    result = service.ask(identity, conversation.conversation_id, "no, ya sé que dan 0")
    assert result["metadata"]["intent"] == "decline_verification"
    assert "dudando" not in result["answer"].lower()
    assert "otro ejercicio" in result["answer"].lower()


def test_other_exercise_advances_without_retrieval_drift(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Ayúdame a factorizar x² - 5x + 6")
    result = service.ask(identity, conversation.conversation_id, "otro ejercicio")
    assert result["metadata"]["intent"] == "exercise_request"
    assert "factoriza" in result["answer"].lower()


def test_current_exercise_is_solved_before_next_exercise_and_coefficients_stay_scoped(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "Ayúdame a factorizar x² - 5x + 6")
    service.ask(identity, conversation.conversation_id, "otro ejercicio")
    solved = service.ask(identity, conversation.conversation_id, "resuélvelo tú y luego vemos otro ejercicio")
    assert solved["metadata"]["intent"] == "solve_current_exercise"
    assert "x² + 5x + 6" in solved["answer"]
    clarification = service.ask(identity, conversation.conversation_id, "¿por qué habías dicho -5?")
    assert clarification["metadata"]["intent"] == "clarify_exercise_transition"
    assert "ejercicio anterior" in clarification["answer"].lower()
    assert "coeficiente de x es +5" in clarification["answer"]
