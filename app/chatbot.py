#!/usr/bin/env python3
from __future__ import annotations
from ai_tutor.tutoring.tutor import Tutor
from ai_tutor.experiments.registry import FAMILIES,resolve_provider,validate_condition
import re

TUTOR=Tutor()
TUTORS={"instructional":TUTOR}

def format_for_chat(text):
    """Elimina delimitadores LaTeX que hacen ruido en la interfaz."""
    text=re.sub(r"\\\((.*?)\\\)",r"\1",text,flags=re.DOTALL)
    text=re.sub(r"\\\[(.*?)\\\]",r"\1",text,flags=re.DOTALL)
    text=re.sub(r"(?<!\\)\$([^$\n]+)\$",r"\1",text)
    return text.replace(r"\$","$")

def ask_backend(question,method="rag",debug=False,provider="instructional",knowledge_mode="instructional",student_profile="unknown"):
    try:
        if provider not in TUTORS: TUTORS[provider]=Tutor(generator_provider=provider)
        tutor=TUTORS[provider]
        response=tutor.ask(question,method,knowledge_mode=knowledge_mode,student_profile=student_profile)
    except Exception as exc:
        return f"No se pudo iniciar el generador {provider}: {exc}",{"method":method,"provider":provider,"error":str(exc)}
    detail={"pedagogical_trace":response.pedagogical_trace or "No disponible para la condición LLM normal.","method":method,"latency_ms":round(response.total_latency_ms,2),"chunks":[c.chunk_id for c in response.retrieval.chunks],"concepts":response.retrieval.concepts}
    if debug: detail["debug_info"]=response.retrieval.debug_info
    detail["provider"]=provider; detail["knowledge_mode"]=knowledge_mode; detail["student_profile"]=student_profile
    return format_for_chat(response.answer),detail

def compare_backend(question,debug=False,provider="local_base"):
    rows=[]
    conditions=[("LLM base · sin base","rag","none",provider),("LLM base · RAG instruccional","rag","instructional",provider),("LLM base · Graph-RAG","graph_rag","instructional",provider),("LLM base · PEP-SA-RAG","pep_sa_rag","instructional",provider)]
    for label,method,knowledge,generator in conditions:
        answer,detail=ask_backend(question,method,debug,generator,knowledge)
        rows.append({"condition":label,"method":method,"knowledge_mode":knowledge,"answer":answer,"latency_ms":detail.get("latency_ms"),
                     "retrieved_concepts":detail.get("concepts",[]),"retrieved_chunks":detail.get("chunks",[]),
                     "prerequisites":detail.get("debug_info",{}).get("prerequisites_activated",[]),
                     "retrieval_scores":detail.get("debug_info",{}).get("fused_ranking",[])})
    return rows

def chat_backend(question,history,method="rag",debug=False,provider="instructional",knowledge_mode="instructional"):
    answer,detail=ask_backend(question,method,debug,provider,knowledge_mode)
    history=(history or [])+[(question,answer)]
    return history,detail,""

def ask_experiment_backend(question,family,adaptation,instructional_condition,retrieval_method,debug=False,student_profile="unknown"):
    try:
        effective_retrieval=retrieval_method if instructional_condition=="instructional_database" else "none"
        validate_condition(family,adaptation,instructional_condition,effective_retrieval)
        provider=resolve_provider(family,adaptation)
        method=retrieval_method if effective_retrieval!="none" else "rag"
        return ask_backend(question,method,debug,provider,instructional_condition,student_profile)
    except Exception as exc:
        return f"Condición no disponible: {exc}",{"error":str(exc),"family":family,"adaptation":adaptation}

def experiment_chat_backend(question,history,family,adaptation,instructional_condition,retrieval_method,debug=False,student_profile="unknown"):
    answer,detail=ask_experiment_backend(question,family,adaptation,instructional_condition,retrieval_method,debug,student_profile)
    return (history or [])+[(question,answer)],detail,""

def compare_experiment_backend(question,family,debug=False,student_profile="unknown"):
    conditions=[]
    for adaptation in ("original","finetuned"):
        if adaptation=="finetuned" and not FAMILIES[family].finetuned_provider: continue
        conditions.extend([
          (adaptation,"raw","none"),(adaptation,"pedagogical_prompt","none"),
          (adaptation,"instructional_database","rag"),(adaptation,"instructional_database","graph_rag"),(adaptation,"instructional_database","pep_sa_rag"),(adaptation,"instructional_database","pep_plan_rag")])
    rows=[]
    for adaptation,condition,retrieval in conditions:
        answer,detail=ask_experiment_backend(question,family,adaptation,condition,retrieval,debug,student_profile)
        rows.append({"family":family,"adaptation":adaptation,"instructional_condition":condition,"retrieval":retrieval,"answer":answer,
                     "latency_ms":detail.get("latency_ms"),"concepts":detail.get("concepts",[]),"chunks":detail.get("chunks",[])})
    return rows

def main():
    try:
        import gradio as gr
    except ImportError:
        raise SystemExit("Install UI dependencies with: pip install -e '.[ui]'")
    with gr.Blocks(title="Tutor de Precálculo") as demo:
        gr.Markdown("# Tutor experimental de Precálculo")
        with gr.Tab("Tutor"):
            family=gr.Dropdown([(value.label,key) for key,value in FAMILIES.items()],value="gemini",label="Familia del modelo")
            adaptation=gr.Radio([("Original","original"),("Fine-tuned","finetuned")],value="original",label="Adaptación")
            condition=gr.Radio([("LLM normal","raw"),("Prompt pedagógico sin base","pedagogical_prompt"),("Base instruccional","instructional_database")],value="raw",label="Condición instruccional")
            method=gr.Radio([("Sin recuperación","none"),("RAG","rag"),("Graph-RAG","graph_rag"),("PEP-SA-RAG v2","pep_sa_rag"),("PEP-Plan-RAG v3","pep_plan_rag")],value="none",label="Recuperación")
            student_profile=gr.Dropdown([("Estado desconocido","unknown"),("Dominio alto","high_mastery"),("Brecha de álgebra","algebra_gap"),("Brecha de prerrequisitos","prerequisite_gap"),("Posible concepción errónea","misconception")],value="unknown",label="Perfil del estudiante (usado por v3)")
            debug=gr.Checkbox(label="Debug / Research mode")
            with gr.Row():
                with gr.Column(scale=3):
                    chat=gr.Chatbot(label="Respuesta para el estudiante",height=460)
                with gr.Column(scale=2):
                    details=gr.JSON(label="Traza pedagógica y panel experimental",height=460)
            question=gr.Textbox(label="Pregunta",placeholder="¿Cómo encuentro el dominio de una función racional?")
            send=gr.Button("Preguntar",variant="primary")
            send.click(experiment_chat_backend,[question,chat,family,adaptation,condition,method,debug,student_profile],[chat,details,question])
            question.submit(experiment_chat_backend,[question,chat,family,adaptation,condition,method,debug,student_profile],[chat,details,question])
            gr.ClearButton([question,chat,details],value="Limpiar")
        with gr.Tab("Comparar métodos"):
            compare_question=gr.Textbox(label="Misma pregunta para los tres métodos")
            compare_debug=gr.Checkbox(label="Incluir debug")
            compare_family=gr.Dropdown([(value.label,key) for key,value in FAMILIES.items()],value="gemini",label="Familia")
            compare_profile=gr.Dropdown([("Estado desconocido","unknown"),("Dominio alto","high_mastery"),("Brecha de álgebra","algebra_gap"),("Brecha de prerrequisitos","prerequisite_gap"),("Posible concepción errónea","misconception")],value="unknown",label="Perfil para PEP-Plan-RAG v3")
            comparison=gr.JSON(label="RAG vs Graph-RAG vs PEP-SA-RAG v2 vs PEP-Plan-RAG v3")
            gr.Button("Ejecutar matriz",variant="primary").click(compare_experiment_backend,[compare_question,compare_family,compare_debug,compare_profile],comparison)
    # Gradio 4 on Python 3.9 can fail while materializing its optional API
    # schema with newer Pydantic versions; the research UI does not expose an API.
    demo.launch(show_api=False)
if __name__=="__main__": main()
