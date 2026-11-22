from ai_tutor.api.services import TutorApplicationService
from ai_tutor.memory import ConversationRepository


def _service(tmp_path):
    service = TutorApplicationService(repository=ConversationRepository(tmp_path / "state.sqlite3"))
    service.default_provider = "instructional"
    service.fallback_providers = []
    session = service.auth.register("context-student", "Context Student", "1234")
    service.repository.save_protocol_acceptance(session["user_id"], service._protocol_version(), True)
    identity = service.auth.require(session)
    conversation = service.memory.create(identity["user_id"])
    return service, identity, conversation


def test_example_request_then_no_and_expression_stays_on_domain_topic(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "¿Cómo encuentro el dominio de una función racional?")
    declined = service.ask(identity, conversation.conversation_id, "no")
    assert declined["metadata"]["intent"] == "decline_example"
    assert "f(x)" in declined["answer"]

    submitted = service.ask(identity, conversation.conversation_id, "1/(x+2)")
    assert submitted["metadata"]["intent"] == "student_example"
    assert "x = -2" in submitted["answer"]
    assert "dificultad aparente" not in submitted["answer"].lower()
    assert "sistemas lineales" not in submitted["answer"].lower()


def test_short_uncertain_turn_does_not_change_active_topic(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "¿Cuál es la diferencia entre relación y función?")
    result = service.ask(identity, conversation.conversation_id, "mmm")
    assert result["metadata"]["intent"] == "feedback_uncertain"
    assert "relación" in result["answer"].lower() or "función" in result["answer"].lower()


def test_bare_no_after_conceptual_question_is_not_a_new_topic(tmp_path):
    service, identity, conversation = _service(tmp_path)
    service.ask(identity, conversation.conversation_id, "¿Cuál es la diferencia entre relación y función?")
    result = service.ask(identity, conversation.conversation_id, "no")
    assert result["metadata"]["intent"] == "feedback_uncertain"
    assert "sistemas lineales" not in result["answer"].lower()
