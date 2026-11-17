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
