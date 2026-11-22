from types import SimpleNamespace

from ai_tutor.memory.contextualizer import contextualize
from ai_tutor.memory.service import ConversationMemory


def test_short_numeric_followup_keeps_active_problem_and_latest_tutor_question():
    messages = [
        SimpleNamespace(role="user", content="Quiero repasar Suma, resta y multiplicación por escalares de matrices"),
        SimpleNamespace(role="assistant", content="Si una matriz tiene 4 y otra 3 en la misma posición, ¿qué número resulta?"),
    ]
    query = contextualize("7", messages, messages[0].content)
    assert "matrices" in query.lower()
    assert "matriz tiene 4" in query.lower()
    assert "7" in query


def test_active_problem_detects_matrix_topic(tmp_path):
    class Repository:
        pass

    memory = ConversationMemory(Repository())
    assert "matrices" in memory._active_problem("Quiero repasar suma y resta de matrices").lower()
