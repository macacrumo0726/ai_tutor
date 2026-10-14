from __future__ import annotations
from dataclasses import dataclass
from ai_tutor.generation.factory import create_generator
from ai_tutor.retrieval.factory import load_retriever
from ai_tutor.utils.paths import project_path
from ai_tutor.utils.paths import load_config
from ai_tutor.utils.io import read_jsonl
from ai_tutor.retrieval.base import RetrievalResult
import re

@dataclass
class TutorResponse:
    answer:str
    retrieval:object
    generation_latency_ms:float
    total_latency_ms:float
    pedagogical_trace:str=""
    generation_error:str=""
    generation_provider:str=""
    generation_model:str=""
    model_fallback_used:bool=False
    primary_generation_error:str=""
    attempted_models:tuple=()

def split_tutor_output(text:str):
    student=re.search(r"<student_response>\s*(.*?)\s*</student_response>",text,re.DOTALL|re.IGNORECASE)
    trace=re.search(r"<instructional_trace>\s*(.*?)\s*</instructional_trace>",text,re.DOTALL|re.IGNORECASE)
    if not student:
        return text.strip(),trace.group(1).strip() if trace else ""
    return student.group(1).strip(),trace.group(1).strip() if trace else ""

class Tutor:
    def __init__(self,generator=None,generator_provider="instructional"):
        self.generator=generator or create_generator(generator_provider); self._retrievers={}
        cfg=load_config(); concepts=read_jsonl(project_path(cfg["paths"]["concepts"]))
        self.concept_labels={c["concept_id"]:c["concept_name"] for c in concepts}
    def ask(self,question:str,retrieval_method:str="rag",top_k:int=5,knowledge_mode:str="instructional_database",student_profile="unknown",conversation_context:str="",retrieval_query:str=None)->TutorResponse:
        import time
        start=time.perf_counter()
        if knowledge_mode in {"none","raw","pedagogical_prompt"}:
            result=RetrievalResult(question,[],[],[],{"method":"none"},0.0,{"retrieval_latency_ms":0.0})
            if knowledge_mode in {"none","raw"}:
                prompt=(f"Contexto de la conversación:\n{conversation_context}\n\nMensaje actual:\n{question}"
                        if conversation_context else question)
            else:
                template=project_path("prompts/precalculus_tutor.txt").read_text(encoding="utf-8")
                prompt=template.format(question=question,conversation_context=conversation_context or "No hay conversación previa.",context="No se proporcionó evidencia recuperada.",concepts="no disponibles",prerequisites="no disponibles",tutorial_plan="no disponible")
            generated=self.generator.generate(prompt)
            raw_answer=generated.text if generated.success else f"No fue posible usar el generador configurado: {generated.error}"
            answer,trace=split_tutor_output(raw_answer)
            return TutorResponse(answer,result,generated.latency_ms,(time.perf_counter()-start)*1000,trace,
                                 generated.error or "",generated.provider,generated.model,
                                 generated.fallback_used,generated.primary_error or "",
                                 generated.attempted_models)
        retriever=self._retrievers.setdefault(retrieval_method,load_retriever(retrieval_method))
        effective_query=retrieval_query or question
        result=retriever.retrieve(effective_query,top_k,student_profile=student_profile,
                                  student_state=student_profile); prerequisites=result.debug_info.get("prerequisites_activated",[])
        # Chunk IDs remain in debug metadata, never in the student-facing prompt.
        context="\n\n".join(c.text for c in result.chunks)
        template=project_path("prompts/precalculus_tutor.txt").read_text(encoding="utf-8")
        concept_labels=[self.concept_labels.get(c,c.replace("_"," ")) for c in result.concepts]
        prerequisite_labels=[self.concept_labels.get(c,c.replace("_"," ")) for c in prerequisites]
        plan=result.debug_info.get("tutorial_plan",{})
        plan_text="; ".join(f"{key}: {value}" for key,value in plan.items()) if plan else "no disponible"
        prompt=template.format(question=question,conversation_context=conversation_context or "No hay conversación previa.",context=context,concepts=", ".join(concept_labels),prerequisites=", ".join(prerequisite_labels),tutorial_plan=plan_text)
        generated=self.generator.generate(prompt)
        raw_answer=generated.text if generated.success else f"No fue posible usar el generador configurado: {generated.error}"
        answer,trace=split_tutor_output(raw_answer)
        return TutorResponse(answer,result,generated.latency_ms,(time.perf_counter()-start)*1000,trace,
                             generated.error or "",generated.provider,generated.model,
                             generated.fallback_used,generated.primary_error or "",
                             generated.attempted_models)
