import pytest

from ai_tutor.memory import ConversationMemory, ConversationRepository


@pytest.fixture
def memory(tmp_path):
    return ConversationMemory(ConversationRepository(tmp_path / "memory.sqlite3"), recent_messages=4,
                              summarize_after=4, summary_max_chars=300)


def test_conversations_persist_and_are_isolated_by_user(memory):
    conversation=memory.create("student_a")
    memory.record_turn("student_a",conversation.conversation_id,"¿Cuánto vale x?","x vale 3")
    reloaded=memory.repository.get_conversation("student_a",conversation.conversation_id,with_messages=True)
    assert [item.content for item in reloaded.messages]==["¿Cuánto vale x?","x vale 3"]
    with pytest.raises(KeyError):
        memory.repository.get_conversation("student_b",conversation.conversation_id)


def test_short_answer_is_contextualized_for_retrieval(memory):
    conversation=memory.create("student")
    memory.record_turn("student",conversation.conversation_id,
                       "Para f(x)=1/(x-3), ¿qué valor hace cero el denominador?","Inténtalo sustituyendo un valor.")
    prepared=memory.prepare("student",conversation.conversation_id,"x = 3")
    assert "f(x)=1/(x-3)" in prepared["retrieval_query"]
    assert "x = 3" in prepared["retrieval_query"]
    assert "Últimos turnos" in prepared["conversation_context"]


def test_long_conversation_creates_summary_and_active_problem(memory):
    conversation=memory.create("student")
    for index in range(3):
        memory.record_turn("student",conversation.conversation_id,f"Resuelve x²={index}",f"Turno {index}")
    result=memory.repository.get_conversation("student",conversation.conversation_id)
    assert result.summary
    assert result.active_problem=="Resuelve x²=2"
    assert result.title.startswith("Resuelve x²=0")


def test_user_id_is_normalized(memory):
    assert memory.repository.ensure_user(" Estudiante 01! ")=="estudiante01"


def test_new_conversation_has_distinct_context(memory):
    first=memory.create("student")
    memory.record_turn("student",first.conversation_id,"Resuelve x²=9","Probemos las raíces.")
    second=memory.create("student")
    assert second.conversation_id != first.conversation_id
    assert memory.chat_history("student",second.conversation_id) == []
    prepared=memory.prepare("student",second.conversation_id,"¿y ahora?")
    assert "x²=9" not in prepared["retrieval_query"]
