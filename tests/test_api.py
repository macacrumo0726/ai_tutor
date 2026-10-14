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


def _register(client, user_id="student", display_name="Student", pin="1234"):
    response = client.post("/api/auth/register", json={
        "user_id": user_id, "display_name": display_name, "pin": pin,
    })
    assert response.status_code == 200
    return response.json()


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


def test_research_routes_require_researcher(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_TUTOR_RESEARCHER_IDS", "researcher")
    client, _ = _client(tmp_path, monkeypatch)
    student = _register(client)
    researcher = _register(client, "researcher", "Researcher")
    student_headers = {"Authorization": f"Bearer {student['token']}"}
    research_headers = {"Authorization": f"Bearer {researcher['token']}"}
    assert client.get("/api/admin/overview", headers=student_headers).status_code == 403
    assert client.get("/api/admin/overview", headers=research_headers).status_code == 200


def test_researcher_can_review_persisted_conversation_messages(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_TUTOR_RESEARCHER_IDS", "researcher")
    client, service = _client(tmp_path, monkeypatch)
    _register(client, "student", "Student")
    researcher = _register(client, "researcher", "Researcher")
    conversation = service.memory.create("student", title="Dominio")
    service.memory.record_turn("student", conversation.conversation_id, "¿Qué es el dominio?", "Son las entradas permitidas.")

    response = client.get(
        "/api/admin/users/student",
        headers={"Authorization": f"Bearer {researcher['token']}"},
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
