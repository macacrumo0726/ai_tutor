import pytest
from app.chatbot import ask_backend,compare_backend,chat_backend,format_for_chat
from ai_tutor.retrieval.factory import load_retriever

def test_unknown_retriever_rejected():
    with pytest.raises(ValueError): load_retriever("magic")

def test_chatbot_backend(monkeypatch,baseline):
    monkeypatch.setattr("ai_tutor.tutoring.tutor.load_retriever",lambda method:baseline)
    answer,details=ask_backend("¿Qué es una ecuación?","rag",True)
    assert answer and details["method"]=="rag" and details["chunks"]

def test_compare_backend(monkeypatch,baseline):
    monkeypatch.setattr("ai_tutor.tutoring.tutor.load_retriever",lambda method:baseline)
    import app.chatbot as chatbot
    chatbot.TUTOR._retrievers.clear()
    rows=compare_backend("dominio",False)
    assert [r["method"] for r in rows]==["rag","rag","graph_rag","pep_sa_rag"]

def test_chat_history_backend(monkeypatch,baseline):
    monkeypatch.setattr("ai_tutor.tutoring.tutor.load_retriever",lambda method:baseline)
    import app.chatbot as chatbot
    chatbot.TUTOR._retrievers.clear()
    history,details,cleared=chat_backend("dominio",[],"rag",False)
    assert len(history)==1 and history[0][0]=="dominio" and details["method"]=="rag" and cleared==""

def test_normal_llm_mode_skips_retrieval(monkeypatch):
    class Generator:
        def generate(self,prompt):
            from ai_tutor.generation.base import GenerationResult
            return GenerationResult("respuesta normal","test","base",1)
    from ai_tutor.tutoring.tutor import Tutor
    tutor=Tutor(generator=Generator())
    response=tutor.ask("pregunta",knowledge_mode="none")
    assert response.answer=="respuesta normal" and response.retrieval.metadata["method"]=="none" and not response.retrieval.chunks

def test_chat_formatter_removes_math_delimiters():
    text="¿Qué valor de $x$ excluimos? También \\(y\\) y \\[x^2+1\\]."
    assert format_for_chat(text)=="¿Qué valor de x excluimos? También y y x^2+1."

def test_tutor_separates_student_answer_and_pedagogical_trace():
    from ai_tutor.tutoring.tutor import split_tutor_output
    text="<student_response>Probemos con x = 2.</student_response><instructional_trace>Activa sustitución.</instructional_trace>"
    answer,trace=split_tutor_output(text)
    assert answer=="Probemos con x = 2." and trace=="Activa sustitución."
