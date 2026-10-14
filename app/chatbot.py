#!/usr/bin/env python3
from __future__ import annotations
from ai_tutor.tutoring.tutor import Tutor
from ai_tutor.assessment import AssessmentService,UnderstandingEvaluator
from ai_tutor.experiments.registry import FAMILIES,resolve_provider,validate_condition
from ai_tutor.memory import (AuthenticationService,ConversationMemory,ConversationRepository,
                             LearningProfileService)
from ai_tutor.utils.paths import load_config,project_path
from ai_tutor.utils.io import read_jsonl
import re

TUTOR=Tutor()
TUTORS={"instructional":TUTOR}
_CONFIG=load_config()
REPOSITORY=ConversationRepository(project_path(_CONFIG["paths"]["conversations"]))
MEMORY=ConversationMemory(
    REPOSITORY,
    **_CONFIG.get("memory",{}),
)
AUTH=AuthenticationService(REPOSITORY)
LEARNING=LearningProfileService(REPOSITORY)
_CONCEPTS=read_jsonl(project_path(_CONFIG["paths"]["concepts"]))
_CONCEPT_LABELS={item["concept_id"]:item.get("concept_name",item["concept_id"]) for item in _CONCEPTS}
_CONCEPT_PREREQUISITES={item["concept_id"]:item.get("prerequisites",[]) for item in _CONCEPTS}
ASSESSMENT=AssessmentService(REPOSITORY,LEARNING,_CONCEPT_LABELS,_CONCEPT_PREREQUISITES)
UNDERSTANDING_EVALUATOR=UnderstandingEvaluator()

def format_for_chat(text):
    """Elimina delimitadores LaTeX que hacen ruido en la interfaz."""
    text=re.sub(r"\\\((.*?)\\\)",r"\1",text,flags=re.DOTALL)
    text=re.sub(r"\\\[(.*?)\\\]",r"\1",text,flags=re.DOTALL)
    text=re.sub(r"(?<!\\)\$([^$\n]+)\$",r"\1",text)
    return text.replace(r"\$","$")

def ask_backend(question,method="rag",debug=False,provider="instructional",knowledge_mode="instructional",student_profile="unknown",conversation_context="",retrieval_query=None,allow_fallback=True):
    try:
        if provider not in TUTORS: TUTORS[provider]=Tutor(generator_provider=provider)
        tutor=TUTORS[provider]
        response=tutor.ask(question,method,knowledge_mode=knowledge_mode,student_profile=student_profile,
                           conversation_context=conversation_context,retrieval_query=retrieval_query)
    except Exception as exc:
        return f"No se pudo iniciar el generador {provider}: {exc}",{"method":method,"provider":provider,"error":str(exc)}
    requested_error=response.generation_error
    fallback_used=False
    if requested_error and allow_fallback and provider!="instructional":
        fallback=TUTORS["instructional"].ask(
            question,method,knowledge_mode=knowledge_mode,student_profile=student_profile,
            conversation_context=conversation_context,retrieval_query=retrieval_query)
        response=fallback
        fallback_used=True
    detail={"pedagogical_trace":response.pedagogical_trace or "No disponible para la condición LLM normal.","method":method,"latency_ms":round(response.total_latency_ms,2),"chunks":[c.chunk_id for c in response.retrieval.chunks],"concepts":response.retrieval.concepts}
    if debug: detail["debug_info"]=response.retrieval.debug_info
    profile_id=getattr(student_profile,"profile_id",student_profile)
    detail.update({"provider":provider,"requested_provider":provider,
                   "effective_provider":"instructional" if fallback_used else provider,
                   "fallback_used":fallback_used,"generation_error":requested_error or None,
                   "effective_model":response.generation_model,
                   "model_fallback_used":response.model_fallback_used,
                   "primary_generation_error":response.primary_generation_error or None,
                   "attempted_models":list(response.attempted_models),
                   "knowledge_mode":knowledge_mode,"student_profile":profile_id})
    answer=format_for_chat(response.answer)
    if fallback_used:
        answer=("El modelo seleccionado no está disponible temporalmente. "
                "Respondí con el tutor local de respaldo para no interrumpir la conversación.\n\n"+answer)
    return answer,detail

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

def ask_experiment_backend(question,family,adaptation,instructional_condition,retrieval_method,debug=False,student_profile="unknown",conversation_context="",retrieval_query=None,allow_fallback=True):
    try:
        effective_retrieval=retrieval_method if instructional_condition=="instructional_database" else "none"
        validate_condition(family,adaptation,instructional_condition,effective_retrieval)
        provider=resolve_provider(family,adaptation)
        method=retrieval_method if effective_retrieval!="none" else "rag"
        return ask_backend(question,method,debug,provider,instructional_condition,student_profile,
                           conversation_context,retrieval_query,allow_fallback)
    except Exception as exc:
        return f"Condición no disponible: {exc}",{"error":str(exc),"family":family,"adaptation":adaptation}

def experiment_chat_backend(question,history,family,adaptation,instructional_condition,retrieval_method,debug=False,student_profile="unknown"):
    answer,detail=ask_experiment_backend(question,family,adaptation,instructional_condition,retrieval_method,debug,student_profile)
    return (history or [])+[(question,answer)],detail,""

def _conversation_choices(user_id):
    return [(item.title,item.conversation_id) for item in MEMORY.repository.list_conversations(user_id)]

def _dropdown_update(choices,value=None):
    import gradio as gr
    return gr.update(choices=choices,value=value)

def initialize_user_backend(user_id):
    user_id=MEMORY.repository.ensure_user(user_id)
    conversations=MEMORY.repository.list_conversations(user_id)
    if not conversations:
        conversation=MEMORY.create(user_id)
    else:
        conversation=conversations[0]
    history=MEMORY.chat_history(user_id,conversation.conversation_id)
    detail={"user_id":user_id,"conversation_id":conversation.conversation_id,"title":conversation.title,
            "memory":"persistent_sqlite","messages":len(history)*2}
    return history,detail,conversation.conversation_id,_dropdown_update(_conversation_choices(user_id),conversation.conversation_id),user_id

def authenticate_backend(user_id,pin,display_name,action):
    try:
        session=AUTH.register(user_id,display_name or user_id,pin) if action=="register" else AUTH.login(user_id,pin)
        history,detail,conversation_id,choices,normalized=initialize_user_backend(session["user_id"])
        detail.update({"authenticated":True,"role":session["role"],"display_name":session["display_name"]})
        return session,f"Sesión iniciada: {session['display_name']} ({session['role']})",normalized,history,detail,conversation_id,choices
    except Exception as exc:
        return {},f"No fue posible iniciar sesión: {exc}","",[],{"authenticated":False,"error":str(exc)},"",_dropdown_update([],None)

def logout_backend(session):
    AUTH.logout(session)
    return {},"Sesión cerrada","",[],{},"",_dropdown_update([],None)

def authenticated_controls(result, control_count):
    """Append a single interactive state to every protected Gradio component."""
    import gradio as gr
    enabled=bool(result[0].get("authenticated"))
    return (*result,*[gr.update(interactive=enabled) for _ in range(control_count)])

def authenticated_load_backend(session,conversation_id=None):
    try:
        identity=AUTH.require(session)
        if conversation_id:
            return load_conversation_backend(identity["user_id"],conversation_id)
        history,detail,cid,choices,_=initialize_user_backend(identity["user_id"])
        return history,detail,cid,choices
    except Exception as exc:
        return [],{"error":str(exc)},"",_dropdown_update([],None)

def authenticated_new_conversation_backend(session,retrieval_method="rag",student_profile="persistent"):
    try:
        identity=AUTH.require(session)
        return new_conversation_backend(identity["user_id"],retrieval_method,student_profile)
    except Exception as exc:
        return [],{"error":str(exc)},"",_dropdown_update([],None),""

def new_conversation_backend(user_id,retrieval_method="rag",student_profile="unknown"):
    conversation=MEMORY.create(user_id,retrieval_method=retrieval_method,student_profile=student_profile)
    detail={"user_id":conversation.user_id,"conversation_id":conversation.conversation_id,
            "title":conversation.title,"memory":"persistent_sqlite"}
    return [],detail,conversation.conversation_id,_dropdown_update(_conversation_choices(user_id),conversation.conversation_id),""

def load_conversation_backend(user_id,conversation_id):
    if not conversation_id:
        return initialize_user_backend(user_id)[:4]
    conversation=MEMORY.repository.get_conversation(user_id,conversation_id)
    history=MEMORY.chat_history(user_id,conversation_id)
    detail={"user_id":conversation.user_id,"conversation_id":conversation_id,"title":conversation.title,
            "summary":conversation.summary,"active_problem":conversation.active_problem,
            "memory":"persistent_sqlite","turns":len(history)}
    return history,detail,conversation_id,_dropdown_update(_conversation_choices(user_id),conversation_id)

def memory_chat_backend(question,history,user_id,conversation_id,family,adaptation,instructional_condition,
                        retrieval_method,debug=False,student_profile="unknown",use_memory=True):
    if not use_memory:
        chat,detail,cleared=experiment_chat_backend(question,history,family,adaptation,instructional_condition,
                                                    retrieval_method,debug,student_profile)
        detail["memory"]="disabled"
        return chat,detail,cleared,conversation_id,_dropdown_update(_conversation_choices(user_id),conversation_id)
    if not conversation_id:
        conversation=MEMORY.create(user_id,retrieval_method=retrieval_method,student_profile=student_profile)
        conversation_id=conversation.conversation_id
    prepared=MEMORY.prepare(user_id,conversation_id,question)
    answer,detail=ask_experiment_backend(
        question,family,adaptation,instructional_condition,retrieval_method,debug,student_profile,
        prepared["conversation_context"],prepared["retrieval_query"],
    )
    profile_id=getattr(student_profile,"profile_id",student_profile)
    metadata={"retrieval_method":retrieval_method,"model_provider":detail.get("provider",family),
              "student_profile":profile_id,"retrieval_query":prepared["retrieval_query"],
              "chunks":detail.get("chunks",[]),"concepts":detail.get("concepts",[]),
              "latency_ms":detail.get("latency_ms")}
    conversation=MEMORY.record_turn(user_id,conversation_id,question,answer,metadata)
    detail.update({"memory":"persistent_sqlite","conversation_id":conversation_id,
                   "conversation_title":conversation.title,"retrieval_query":prepared["retrieval_query"],
                   "conversation_summary":conversation.summary,"active_problem":conversation.active_problem})
    return MEMORY.chat_history(user_id,conversation_id),detail,"",conversation_id,_dropdown_update(_conversation_choices(user_id),conversation_id)

def authenticated_memory_chat_backend(question,history,session,user_id,conversation_id,family,adaptation,
                                      instructional_condition,retrieval_method,debug=False,
                                      student_profile="persistent",use_memory=True):
    try:
        identity=AUTH.require(session)
        if identity["user_id"] != REPOSITORY.normalize_user_id(user_id):
            raise PermissionError("La sesión no corresponde al usuario solicitado")
        prior_messages=(REPOSITORY.list_messages(user_id,conversation_id)
                        if conversation_id else [])
        effective_profile=(LEARNING.state_for(identity["user_id"])
                           if student_profile=="persistent" else student_profile)
        result=memory_chat_backend(question,history,user_id,conversation_id,family,adaptation,
                                   instructional_condition,retrieval_method,debug,effective_profile,use_memory)
        chat,detail,cleared,conversation_id,choices=result
        concepts=detail.get("concepts",[])
        detail["profile_source"]="persistent_database" if student_profile=="persistent" else "synthetic_profile"
        detail["student_state_used"]=(effective_profile.to_dict() if hasattr(effective_profile,"to_dict") else student_profile)
        detail["feedback_concepts"]=concepts
        previous_tutor=next((m for m in reversed(prior_messages) if m.role=="assistant"),None)
        previous_concepts=(previous_tutor.metadata.get("concepts",[]) if previous_tutor else concepts)
        evaluation=UNDERSTANDING_EVALUATOR.evaluate(
            question,previous_tutor.content if previous_tutor else "",previous_concepts,_CONCEPT_LABELS)
        REPOSITORY.save_understanding_evaluation(
            user_id,conversation_id,previous_concepts,question,evaluation["classification"],
            evaluation["score"],evaluation["confidence"],evaluation["features"],"heuristic_v1")
        updates=[]
        if evaluation["changes_mastery"]:
            for concept_id in previous_concepts:
                updates.append(REPOSITORY.add_learning_evidence(
                    user_id,concept_id,"heuristic_understanding_evaluation",evaluation["score"],
                    "understanding_evaluator_v1",conversation_id,
                    {"classification":evaluation["classification"],"reason":evaluation["reason"]},
                    evidence_weight=evaluation["confidence"]*.5))
        detail["understanding_evaluation"]={**evaluation,"concept_ids":previous_concepts,
                                             "mastery_updates":updates}
        detail["self_report_comparison"]=REPOSITORY.latest_signal_comparison(user_id,conversation_id)
        if updates: detail["student_state_after_turn"]=LEARNING.state_for(user_id).to_dict()
        REPOSITORY.add_learning_event(user_id,"tutor_turn",{
            "retrieval_method":retrieval_method,"concept_ids":concepts,
            "profile_source":detail["profile_source"],"latency_ms":detail.get("latency_ms")},conversation_id)
        return chat,detail,cleared,conversation_id,choices,concepts
    except Exception as exc:
        return history,{"error":str(exc),"authenticated":False},question,conversation_id,_dropdown_update([],None),[]

def feedback_backend(session,conversation_id,concept_ids,feedback):
    try:
        identity=AUTH.require(session)
        scores={"understood":1.0,"partial":.6,"needs_help":.2}
        report_id=REPOSITORY.save_self_report(identity["user_id"],conversation_id,concept_ids,
                                              feedback,scores[feedback])
        result={"self_report_id":report_id,"signal_type":"student_self_report",
                "report":feedback,"reported_score":scores[feedback],
                "concept_ids":concept_ids,"changes_mastery":False,
                "comparison":REPOSITORY.latest_signal_comparison(identity["user_id"],conversation_id),
                "note":"El botón registra percepción del estudiante; no modifica el dominio estimado."}
        return result,student_profile_backend(session)
    except Exception as exc:
        error={"error":str(exc)}
        return error,error

def student_profile_backend(session):
    try:
        identity=AUTH.require(session)
        report=REPOSITORY.learning_report(identity["user_id"])
        return {"user_id":identity["user_id"],"role":identity["role"],**report}
    except Exception as exc:
        return {"error":str(exc)}

def researcher_users_backend(session):
    try:
        AUTH.require(session,"researcher")
        users=REPOSITORY.list_users()
        return users,_dropdown_update([(f"{u['display_name']} ({u['user_id']})",u["user_id"]) for u in users])
    except Exception as exc:
        return [{"error":str(exc)}],_dropdown_update([],None)

def researcher_report_backend(session,target_user):
    try:
        AUTH.require(session,"researcher")
        conversations=REPOSITORY.list_conversations(target_user,include_archived=True)
        return {"user":REPOSITORY.get_user(target_user),
                "learning":REPOSITORY.learning_report(target_user),
                "conversations":[{"conversation_id":c.conversation_id,"title":c.title,
                                  "updated_at":c.updated_at,"method":c.retrieval_method,
                                  "turns":len(REPOSITORY.list_messages(target_user,c.conversation_id))//2}
                                 for c in conversations]}
    except Exception as exc:
        return {"error":str(exc)}

def create_micro_check_backend(session,concept_ids):
    try:
        AUTH.require(session)
        check=ASSESSMENT.create(concept_ids)
        return check.to_dict(),f"### Comprueba tu aprendizaje\n\n{check.question}",""
    except Exception as exc:
        return {},f"No se pudo crear el micro-check: {exc}",""

def submit_micro_check_backend(session,conversation_id,check_data,answer):
    try:
        identity=AUTH.require(session)
        if not check_data: raise ValueError("Genera primero una pregunta de comprobación")
        result=ASSESSMENT.submit(identity["user_id"],conversation_id,check_data,answer)
        decision=result["decision"]; evaluation=result["evaluation"]
        message=(f"**{'Correcto' if evaluation['correct'] else 'Revisemos'}** · "
                 f"{evaluation['feedback']}\n\nDecisión del tutor: `{decision['action']}`")
        if result.get("hint"): message+=f"\n\n**Pista:** {result['hint']}"
        message+=(f"\n\nDominio estimado: {result['mastery_before']:.2f} → "
                  f"{result['mastery_after']:.2f}")
        return result,message,"",student_profile_backend(session)
    except Exception as exc:
        error={"error":str(exc)}
        return error,f"No se pudo evaluar: {exc}",answer,error

def compare_experiment_backend(question,family,debug=False,student_profile="unknown"):
    conditions=[]
    for adaptation in ("original","finetuned"):
        if adaptation=="finetuned" and not FAMILIES[family].finetuned_provider: continue
        conditions.extend([
          (adaptation,"raw","none"),(adaptation,"pedagogical_prompt","none"),
          (adaptation,"instructional_database","rag"),(adaptation,"instructional_database","graph_rag"),(adaptation,"instructional_database","pep_sa_rag"),(adaptation,"instructional_database","pep_plan_rag")])
    rows=[]
    for adaptation,condition,retrieval in conditions:
        answer,detail=ask_experiment_backend(question,family,adaptation,condition,retrieval,debug,
                                             student_profile,allow_fallback=False)
        rows.append({"family":family,"adaptation":adaptation,"instructional_condition":condition,"retrieval":retrieval,"answer":answer,
                     "latency_ms":detail.get("latency_ms"),"concepts":detail.get("concepts",[]),"chunks":detail.get("chunks",[])})
    return rows

def main():
    try:
        import gradio as gr
    except ImportError:
        raise SystemExit("Install UI dependencies with: pip install -e '.[ui]'")
    css="""
    .hero {background:linear-gradient(120deg,#312e81,#2563eb);color:white;padding:24px;border-radius:18px;margin-bottom:12px}
    .hero h1,.hero p{color:white;margin:0}.hero p{margin-top:7px;opacity:.9}
    .student-panel{border-radius:16px}.primary-action button{min-height:48px;font-size:16px}
    """
    with gr.Blocks(title="Tutor de Precálculo",theme=gr.themes.Soft(primary_hue="indigo",neutral_hue="slate"),css=css) as demo:
        gr.HTML("<div class='hero'><h1>Tu tutor de Precálculo</h1><p>Pregunta, intenta, recibe pistas y construye tu progreso paso a paso.</p></div>")
        auth_session=gr.State({})
        feedback_concepts=gr.State([])
        with gr.Accordion("Acceso",open=True):
            with gr.Row():
                login_user=gr.Textbox(value="test",label="Usuario")
                login_name=gr.Textbox(value="test",label="Nombre visible")
                login_pin=gr.Textbox(value="test",label="PIN",type="password")
            with gr.Row():
                login_button=gr.Button("Iniciar sesión",variant="primary")
                register_button=gr.Button("Crear cuenta")
                logout_button=gr.Button("Cerrar sesión")
            auth_status=gr.Markdown("Inicia sesión o crea una cuenta local. No uses datos personales reales.")
        with gr.Tab("Tutor"):
            with gr.Row():
                user_id=gr.Textbox(value="",label="Usuario autenticado",interactive=False,scale=2)
                load_user=gr.Button("Cargar historial",scale=1,interactive=False)
                conversation_list=gr.Dropdown([],label="Conversaciones anteriores",scale=3,interactive=False)
                new_conversation=gr.Button("+ Nueva conversación",scale=1,interactive=False)
            conversation_id=gr.State("")
            gr.Markdown("La memoria se guarda localmente por usuario seudónimo. No escribas información personal real.")
            family=gr.Dropdown([(value.label,key) for key,value in FAMILIES.items()],value="gemini",
                               label="Modelo que responderá",interactive=False)
            gr.Markdown("Si una API devuelve 503, el chat usa un respaldo local y lo registra en el panel. Las comparaciones experimentales nunca sustituyen el modelo silenciosamente.")
            with gr.Accordion("Configuración del experimento",open=False):
                gr.Markdown("Para estudiantes se recomienda Gemini + base instruccional + PEP‑Plan v3.")
                adaptation=gr.Radio([("Original","original"),("Fine-tuned","finetuned")],value="original",label="Adaptación",interactive=False)
                condition=gr.Radio([("LLM normal","raw"),("Prompt pedagógico sin base","pedagogical_prompt"),("Base instruccional","instructional_database")],value="instructional_database",label="Condición instruccional",interactive=False)
                method=gr.Radio([("Sin recuperación","none"),("RAG","rag"),("Graph-RAG","graph_rag"),("PEP-SA-RAG v2","pep_sa_rag"),("PEP-Plan-RAG v3","pep_plan_rag")],value="pep_plan_rag",label="Recuperación",interactive=False)
                student_profile=gr.Dropdown([("Perfil persistente del estudiante","persistent"),("Estado desconocido (sintético)","unknown"),("Dominio alto (sintético)","high_mastery"),("Brecha de álgebra (sintético)","algebra_gap"),("Brecha de prerrequisitos (sintético)","prerequisite_gap"),("Posible concepción errónea (sintético)","misconception")],value="persistent",label="Perfil del estudiante (v3)",interactive=False)
                use_memory=gr.Checkbox(value=True,label="Usar memoria conversacional",interactive=False)
                debug=gr.Checkbox(label="Debug / Research mode",interactive=False)
            with gr.Row():
                with gr.Column(scale=3):
                    chat=gr.Chatbot(label="Respuesta para el estudiante",height=460)
                with gr.Column(scale=2):
                    details=gr.JSON(label="Traza pedagógica y panel experimental",height=460)
            question=gr.Textbox(label="Pregunta",placeholder="¿Cómo encuentro el dominio de una función racional?",interactive=False)
            send=gr.Button("Preguntar al tutor",variant="primary",interactive=False,elem_classes="primary-action")
            with gr.Row():
                understood=gr.Button("Lo entendí",interactive=False)
                partial=gr.Button("Entendí parcialmente",interactive=False)
                needs_help=gr.Button("Necesito más ayuda",interactive=False)
            gr.Markdown("¿Cómo sentiste tu comprensión? Estos botones guardan un **auto-reporte** y no cambian el dominio estimado. El sistema lo contrasta con una evaluación independiente de tus respuestas.")
            memory_inputs=[question,chat,auth_session,user_id,conversation_id,family,adaptation,condition,method,debug,student_profile,use_memory]
            memory_outputs=[chat,details,question,conversation_id,conversation_list,feedback_concepts]
            send.click(authenticated_memory_chat_backend,memory_inputs,memory_outputs)
            question.submit(authenticated_memory_chat_backend,memory_inputs,memory_outputs)
            load_user.click(authenticated_load_backend,[auth_session],[chat,details,conversation_id,conversation_list])
            conversation_list.change(authenticated_load_backend,[auth_session,conversation_list],[chat,details,conversation_id,conversation_list])
            new_conversation.click(authenticated_new_conversation_backend,[auth_session,method,student_profile],[chat,details,conversation_id,conversation_list,question])
            clear_button=gr.Button("Limpiar y comenzar conversación nueva",interactive=False)
            clear_button.click(authenticated_new_conversation_backend,[auth_session,method,student_profile],
                               [chat,details,conversation_id,conversation_list,question])
        with gr.Tab("Perfil del estudiante"):
            gr.Markdown("El dominio está entre 0 y 1 y conserva la evidencia que produjo cada actualización.")
            profile_view=gr.JSON(label="Perfil longitudinal y evidencia")
            refresh_profile=gr.Button("Actualizar perfil",interactive=False)
            refresh_profile.click(student_profile_backend,[auth_session],profile_view)
        with gr.Tab("Práctica guiada"):
            gr.Markdown("## Comprueba lo aprendido\nEl tutor calificará una pregunta corta y decidirá si avanzar, consolidar, dar una pista o recuperar un prerrequisito.")
            micro_check_state=gr.State({})
            micro_check_prompt=gr.Markdown("Realiza primero una pregunta en el chat para detectar el concepto.")
            micro_check_answer=gr.Textbox(label="Tu respuesta",placeholder="Escribe tu intento aquí…",interactive=False)
            with gr.Row():
                create_check=gr.Button("Generar micro-check",interactive=False)
                submit_check=gr.Button("Comprobar respuesta",variant="primary",interactive=False)
            assessment_feedback=gr.Markdown()
            assessment_detail=gr.JSON(label="Detalle de evaluación y decisión pedagógica")
            create_check.click(create_micro_check_backend,[auth_session,feedback_concepts],
                               [micro_check_state,micro_check_prompt,micro_check_answer])
            submit_check.click(submit_micro_check_backend,
                               [auth_session,conversation_id,micro_check_state,micro_check_answer],
                               [assessment_detail,assessment_feedback,micro_check_answer,profile_view])
        # Feedback wiring is placed after profile_view exists.
        understood.click(lambda s,c,ids: feedback_backend(s,c,ids,"understood"),
                         [auth_session,conversation_id,feedback_concepts],[details,profile_view])
        partial.click(lambda s,c,ids: feedback_backend(s,c,ids,"partial"),
                      [auth_session,conversation_id,feedback_concepts],[details,profile_view])
        needs_help.click(lambda s,c,ids: feedback_backend(s,c,ids,"needs_help"),
                         [auth_session,conversation_id,feedback_concepts],[details,profile_view])
        with gr.Tab("Comparar métodos"):
            compare_question=gr.Textbox(label="Misma pregunta para los tres métodos",interactive=False)
            compare_debug=gr.Checkbox(label="Incluir debug",interactive=False)
            compare_family=gr.Dropdown([(value.label,key) for key,value in FAMILIES.items()],value="gemini",label="Familia",interactive=False)
            compare_profile=gr.Dropdown([("Estado desconocido","unknown"),("Dominio alto","high_mastery"),("Brecha de álgebra","algebra_gap"),("Brecha de prerrequisitos","prerequisite_gap"),("Posible concepción errónea","misconception")],value="unknown",label="Perfil para PEP-Plan-RAG v3",interactive=False)
            comparison=gr.JSON(label="RAG vs Graph-RAG vs PEP-SA-RAG v2 vs PEP-Plan-RAG v3")
            compare_button=gr.Button("Ejecutar matriz",variant="primary",interactive=False)
            compare_button.click(compare_experiment_backend,[compare_question,compare_family,compare_debug,compare_profile],comparison)
        with gr.Tab("Investigación"):
            gr.Markdown("Acceso restringido al rol investigador. Permite auditar perfiles e historiales sin exponer PINs.")
            researcher_users=gr.JSON(label="Usuarios")
            target_user=gr.Dropdown([],label="Usuario a consultar",interactive=False)
            researcher_report=gr.JSON(label="Historial y perfil")
            list_users_button=gr.Button("Listar usuarios",interactive=False)
            report_button=gr.Button("Consultar usuario",interactive=False)
            list_users_button.click(researcher_users_backend,[auth_session],[researcher_users,target_user])
            report_button.click(researcher_report_backend,[auth_session,target_user],researcher_report)
        auth_outputs=[auth_session,auth_status,user_id,chat,details,conversation_id,conversation_list]
        protected=[load_user,conversation_list,new_conversation,family,adaptation,condition,method,
                   student_profile,use_memory,debug,question,send,understood,partial,needs_help,
                   clear_button,refresh_profile,compare_question,compare_debug,compare_family,
                   compare_profile,compare_button,target_user,list_users_button,report_button,
                   micro_check_answer,create_check,submit_check]
        full_auth_outputs=[*auth_outputs,*protected]
        login_button.click(lambda u,p,n: authenticated_controls(authenticate_backend(u,p,n,"login"),len(protected)),
                           [login_user,login_pin,login_name],full_auth_outputs)
        register_button.click(lambda u,p,n: authenticated_controls(authenticate_backend(u,p,n,"register"),len(protected)),
                              [login_user,login_pin,login_name],full_auth_outputs)
        logout_button.click(lambda s: authenticated_controls(logout_backend(s),len(protected)),
                            [auth_session],full_auth_outputs)
    # Gradio 4 on Python 3.9 can fail while materializing its optional API
    # schema with newer Pydantic versions; the research UI does not expose an API.
    demo.launch(show_api=False)
if __name__=="__main__": main()
