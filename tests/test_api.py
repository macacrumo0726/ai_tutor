from fastapi.testclient import TestClient

from ai_tutor.api.app import create_app
from ai_tutor.api.services import (
    TutorApplicationService, _open_question, _response_is_relevant, _response_is_spanish,
    _response_has_prompt_leak, _response_passes_guardrails, _social_intent, _student_text,
)
from ai_tutor.memory import ConversationRepository


def _client(tmp_path, monkeypatch):
    repository = ConversationRepository(tmp_path / "api.sqlite3")
    service = TutorApplicationService(repository=repository)
    service.default_provider = "instructional"
    service.default_retrieval = "rag"
    service.ask = lambda identity, conversation_id, message: {
        "answer": f"Respuesta guiada para: {message}",
        "metadata": {"concepts": ["domain"], "retrieval_method": "rag"},
    }
    return TestClient(create_app(service)), service


def _register(client, user_id="student", display_name="Student", pin="1234", accept=True):
    response = client.post("/api/auth/register", json={
        "user_id": user_id, "display_name": display_name, "pin": pin,
    })
    assert response.status_code == 200
    session = response.json()
    if accept:
        protocol = client.get("/api/protocol").json()
        accepted = client.post("/api/me/protocol/accept", headers={"Authorization": f"Bearer {session['token']}"}, json={
            "protocol_version": protocol["version"], "accepted": True,
        })
        assert accepted.status_code == 200
    return session


def test_response_guardrails_accept_spanish_math_and_reject_leaks_or_wrong_language():
    assert _response_is_spanish("Buscamos dos números que sumen -5 y cuyo producto sea 6.")
    assert _response_passes_guardrails("factoriza x² - 5x + 6", "x² - 5x + 6 = (x - 3)(x - 2)")[0]
    assert _response_has_prompt_leak("<think>internal reasoning</think>")
    assert not _response_passes_guardrails("factoriza x² - 5x + 6", "The answer is (x - 3)(x - 2), because...")[0]


def test_student_flow_is_authenticated_and_isolated(tmp_path, monkeypatch):
    client, _ = _client(tmp_path, monkeypatch)
    session = _register(client)
    headers = {"Authorization": f"Bearer {session['token']}"}
    assert client.get("/api/me", headers=headers).status_code == 200
    assert client.get("/api/conversations", headers=headers).json() == []
    created = client.post("/api/conversations", headers=headers, json={}).json()
    listed = client.get("/api/conversations", headers=headers).json()
    assert [item["conversation_id"] for item in listed] == [created["conversation_id"]]
    loaded = client.get(f"/api/conversations/{created['conversation_id']}", headers=headers).json()
    assert loaded["user_id"] == "student"
    second = _register(client, "student_2", "Second student")
    second_headers = {"Authorization": f"Bearer {second['token']}"}
    assert client.get("/api/conversations", headers=second_headers).json() == []
    assert client.get(f"/api/conversations/{created['conversation_id']}", headers=second_headers).status_code == 404
    assert client.get("/api/conversations").status_code == 401


def test_protocol_blocks_student_until_current_version_is_accepted(tmp_path, monkeypatch):
    client, _ = _client(tmp_path, monkeypatch)
    session = _register(client, accept=False)
    headers = {"Authorization": f"Bearer {session['token']}"}
    assert client.get("/api/me/protocol", headers=headers).json()["accepted_current"] is False
    assert client.get("/api/conversations", headers=headers).status_code == 428
    assert client.post("/api/conversations", headers=headers, json={}).status_code == 428
    protocol = client.get("/api/protocol").json()
    accepted = client.post("/api/me/protocol/accept", headers=headers, json={
        "protocol_version": protocol["version"], "accepted": True,
    })
    assert accepted.status_code == 200
    assert client.get("/api/conversations", headers=headers).status_code == 200


def test_protocol_document_is_available_before_acceptance(tmp_path, monkeypatch):
    client, _ = _client(tmp_path, monkeypatch)
    response = client.get("/api/protocol/document")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")


def test_protocol_rejects_old_version_and_records_utc_acceptance(tmp_path, monkeypatch):
    client, _ = _client(tmp_path, monkeypatch)
    session = _register(client, accept=False)
    headers = {"Authorization": f"Bearer {session['token']}"}
    rejected = client.post("/api/me/protocol/accept", headers=headers, json={
        "protocol_version": "2020-old", "accepted": True,
    })
    assert rejected.status_code == 409
    protocol = client.get("/api/protocol").json()
    accepted = client.post("/api/me/protocol/accept", headers=headers, json={
        "protocol_version": protocol["version"], "accepted": True,
    }).json()
    assert accepted["acceptance"]["accepted"] == 1
    assert accepted["acceptance"]["accepted_at_utc"].endswith("+00:00")


def test_avatar_roundtrip(tmp_path, monkeypatch):
    client, _ = _client(tmp_path, monkeypatch)
    session = _register(client)
    headers = {"Authorization": f"Bearer {session['token']}"}
    payload = {"style": "orbit", "skin_tone": "cocoa", "hair": "curls", "accessory": "glasses", "background": "ocean"}
    response = client.put("/api/me/avatar", headers=headers, json=payload)
    assert response.status_code == 200
    assert client.get("/api/me/avatar", headers=headers).json()["hair"] == "curls"


def test_learning_path_endpoint_returns_adaptive_route(tmp_path, monkeypatch):
    client, _ = _client(tmp_path, monkeypatch)
    session = _register(client)
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = client.get("/api/me/learning-path", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert "mastery_threshold" in payload
    assert isinstance(payload["items"], list)


def test_stream_returns_sse_events(tmp_path, monkeypatch):
    client, _ = _client(tmp_path, monkeypatch)
    session = _register(client)
    headers = {"Authorization": f"Bearer {session['token']}"}
    conversation = client.post("/api/conversations", headers=headers, json={}).json()
    response = client.post(
        f"/api/conversations/{conversation['conversation_id']}/messages/stream",
        headers=headers,
        json={"message": "¿Qué es el dominio?"},
    )
    assert response.status_code == 200
    assert "event: status" in response.text
    assert "event: token" in response.text
    assert "event: done" in response.text


def test_stream_does_not_expose_internal_exception(tmp_path):
    client, service = _client(tmp_path, None)
    session = _register(client)
    headers = {"Authorization": f"Bearer {session['token']}"}
    conversation = client.post("/api/conversations", headers=headers, json={}).json()
    service.ask = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("provider secret token"))
    response = client.post(
        f"/api/conversations/{conversation['conversation_id']}/messages/stream",
        headers=headers,
        json={"message": "¿Qué es una función?"},
    )
    assert response.status_code == 200
    assert "provider secret token" not in response.text
    assert "No fue posible completar la respuesta" in response.text


def test_health_readiness_and_security_headers(tmp_path):
    client, service = _client(tmp_path, None)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.headers["x-content-type-options"] == "nosniff"
    ready = client.get("/api/ready")
    assert ready.status_code in {200, 503}
    if ready.status_code == 200:
        assert ready.json()["retrieval"] == service.default_retrieval


def test_admin_routes_require_admin(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_TUTOR_ADMIN_IDS", "admin_user")
    client, _ = _client(tmp_path, monkeypatch)
    student = _register(client)
    administrator = _register(client, "admin_user", "Administrator")
    student_headers = {"Authorization": f"Bearer {student['token']}"}
    admin_headers = {"Authorization": f"Bearer {administrator['token']}"}
    assert client.get("/api/admin/overview", headers=student_headers).status_code == 403
    assert client.get("/api/admin/overview", headers=admin_headers).status_code == 200


def test_admin_study_panel_excludes_seed_demo_accounts_and_reports_filtered_models(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_TUTOR_ADMIN_IDS", "admin_user")
    client, service = _client(tmp_path, monkeypatch)
    student = _register(client, "participant_1", "Participant")
    demo = _register(client, "test_demo", "Seed demo")
    service.repository.mark_demo_user("test_demo", True)
    administrator = _register(client, "admin_user", "Administrator")
    first = service.memory.create("participant_1", model_provider="gemini", retrieval_method="pep_plan_rag")
    service.memory.record_turn("participant_1", first.conversation_id, "pregunta", "respuesta",
                               {"model_provider": "gemini", "retrieval_method": "pep_plan_rag"})
    second = service.memory.create("participant_1", model_provider="instructional", retrieval_method="rag")
    service.memory.record_turn("participant_1", second.conversation_id, "otra", "respuesta",
                               {"model_provider": "instructional", "retrieval_method": "rag"})
    headers = {"Authorization": f"Bearer {administrator['token']}"}
    users = client.get("/api/admin/users", headers=headers).json()
    assert {item["user_id"] for item in users} == {"participant_1", "admin_user"}
    overview = client.get("/api/admin/overview?user_id=participant_1", headers=headers).json()
    assert set(overview["providers"]) == {"gemini", "instructional"}
    filtered = client.get("/api/admin/overview?user_id=participant_1&model_provider=gemini", headers=headers).json()
    assert filtered["provider"] == "gemini"
    assert filtered["retrieval_method"] == "pep_plan_rag"


def test_admin_can_review_persisted_conversation_messages(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_TUTOR_ADMIN_IDS", "admin_user")
    client, service = _client(tmp_path, monkeypatch)
    _register(client, "student", "Student")
    administrator = _register(client, "admin_user", "Administrator")
    conversation = service.memory.create("student", title="Dominio")
    service.memory.record_turn("student", conversation.conversation_id, "¿Qué es el dominio?", "Son las entradas permitidas.")

    response = client.get(
        "/api/admin/users/student",
        headers={"Authorization": f"Bearer {administrator['token']}"},
    )

    assert response.status_code == 200
    messages = response.json()["conversations"][0]["messages"]
    assert [item["content"] for item in messages] == [
        "¿Qué es el dominio?",
        "Son las entradas permitidas.",
    ]


def test_social_messages_bypass_retrieval_but_remain_in_memory(tmp_path):
    repository = ConversationRepository(tmp_path / "social.sqlite3")
    service = TutorApplicationService(repository=repository)
    identity = service.auth.register("student", "Camila", "1234")
    conversation = service.memory.create("student", title="Nueva conversación")

    result = service.ask(identity, conversation.conversation_id, "hola")

    assert result["answer"].startswith("¡Hola, Camila!")
    assert result["metadata"]["intent"] == "greeting"
    assert result["metadata"]["retrieval_method"] == "none"
    assert result["metadata"]["chunks"] == []
    messages = repository.list_messages("student", conversation.conversation_id)
    assert [(item.role, item.content) for item in messages] == [
        ("user", "hola"),
        ("assistant", result["answer"]),
    ]


def test_social_intent_does_not_capture_mathematical_messages():
    assert _social_intent("buenas tardes") == "greeting"
    assert _social_intent("gracias") == "thanks"
    assert _social_intent("Hola, ¿cómo factorizo x² - 5x + 6?") is None


def test_open_topic_question_bypasses_retrieval(tmp_path):
    repository = ConversationRepository(tmp_path / "open-question.sqlite3")
    service = TutorApplicationService(repository=repository)
    identity = service.auth.register("student", "Estudiante", "1234")
    conversation = service.memory.create("student", title="Nueva conversación")
    result = service.ask(identity, conversation.conversation_id, "¿Qué me puedes explicar?")
    assert _open_question("que me puedes explicar?")
    assert result["metadata"]["intent"] == "open_question"
    assert result["metadata"]["retrieval_method"] == "none"
    assert "¿Qué tema o problema" in result["answer"]


def test_student_text_removes_model_formatting_delimiters():
    assert _student_text("Si `x = 2`, entonces $x$ no pertenece al dominio.") == (
        "Si x = 2, entonces x no pertenece al dominio."
    )


def test_response_guard_rejects_unrelated_retrieval_answer():
    assert _response_is_relevant("Ayúdame a factorizar x² - 5x + 6", "Veamos la función cosecante.") is False
    assert _response_is_relevant("Ayúdame a factorizar x² - 5x + 6", "Buscamos dos factores que sumen -5 y multipliquen 6.") is True


def test_wrong_verified_answer_updates_profile_as_incorrect(tmp_path, monkeypatch):
    repository = ConversationRepository(tmp_path / "verified.sqlite3")
    service = TutorApplicationService(repository=repository)
    identity = service.auth.register("student", "Student", "1234")
    conversation = service.memory.create("student", title="Dominio")
    service.memory.record_turn(
        "student",
        conversation.conversation_id,
        "Dame un ejercicio",
        "Para 1/(x - 5), ¿qué valor hace cero el denominador?",
        {"concepts": ["1_4_dominio_de_una_expresion_algebraica"]},
    )

    class FakeTutor:
        def ask(self, *args, **kwargs):
            from ai_tutor.retrieval.base import RetrievalResult
            from ai_tutor.tutoring.tutor import TutorResponse
            assert "respuesta '8' es INCORRECTA" in kwargs["conversation_context"]
            retrieval = RetrievalResult("8", [], ["1_4_dominio_de_una_expresion_algebraica"], [], {}, 0.0, {})
            return TutorResponse("Revisa: x - 5 = 0 da x = 5, no 8.", retrieval, 0.0, 1.0,
                                 generation_provider="fake", generation_model="fake")

    monkeypatch.setattr(service, "tutor", lambda provider: FakeTutor())
    result = service.ask(identity, conversation.conversation_id, "8")

    assert result["metadata"]["response_verification"]["status"] == "incorrect"
    report = repository.learning_report("student")
    mastery = next(item for item in report["mastery"] if item["concept_id"] == "1_4_dominio_de_una_expresion_algebraica")
    assert mastery["mastery"] < 0.5
    assert report["understanding_evaluations"][0]["classification"] == "not_understood"


def test_all_provider_failures_return_local_emergency_answer(tmp_path, monkeypatch):
    repository = ConversationRepository(tmp_path / "emergency.sqlite3")
    service = TutorApplicationService(repository=repository)
    identity = service.auth.register("student", "Student", "1234")
    conversation = service.memory.create("student", title="Factorización")

    def failing_tutor(_provider):
        raise RuntimeError("simulated provider outage")

    monkeypatch.setattr(service, "tutor", failing_tutor)
    result = service.ask(identity, conversation.conversation_id, "Ayúdame a factorizar x² - 5x + 6")

    assert result["answer"]
    assert result["metadata"]["model_provider"] == "instructional_emergency"
    assert result["metadata"]["fallback_used"] is True
    messages = repository.list_messages("student", conversation.conversation_id)
    assert messages[-1].role == "assistant"
