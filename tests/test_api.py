from fastapi.testclient import TestClient

from ai_tutor.api.app import create_app
from ai_tutor.api.services import TutorApplicationService, _social_intent, _student_text
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


def test_admin_routes_require_admin(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_TUTOR_ADMIN_IDS", "admin_user")
    client, _ = _client(tmp_path, monkeypatch)
    student = _register(client)
    administrator = _register(client, "admin_user", "Administrator")
    student_headers = {"Authorization": f"Bearer {student['token']}"}
    admin_headers = {"Authorization": f"Bearer {administrator['token']}"}
    assert client.get("/api/admin/overview", headers=student_headers).status_code == 403
    assert client.get("/api/admin/overview", headers=admin_headers).status_code == 200


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


def test_student_text_removes_model_formatting_delimiters():
    assert _student_text("Si `x = 2`, entonces $x$ no pertenece al dominio.") == (
        "Si x = 2, entonces x no pertenece al dominio."
    )


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
