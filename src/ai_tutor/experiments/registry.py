from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ModelFamily:
    family_id:str
    label:str
    original_provider:str
    finetuned_provider:Optional[str]
    weights_open:bool
    tuning_mode:str

FAMILIES={
 "qwen3_8b":ModelFamily("qwen3_8b","Qwen3-8B","local_base","local_finetuned",True,"QLoRA local"),
 "deepseek_distill_qwen_7b":ModelFamily("deepseek_distill_qwen_7b","DeepSeek-R1-Distill-Qwen-7B","local_deepseek_base","local_deepseek_finetuned",True,"QLoRA local"),
 "openai":ModelFamily("openai","OpenAI GPT","openai","openai_finetuned",False,"Fine-tuning administrado"),
 "gemini":ModelFamily("gemini","Google Gemini","gemini",None,False,"No disponible en Gemini API"),
 "deepseek_api":ModelFamily("deepseek_api","DeepSeek API","deepseek",None,False,"No disponible sobre el endpoint API"),
}

def resolve_provider(family_id:str,adaptation:str)->str:
    if family_id not in FAMILIES: raise ValueError(f"Familia desconocida: {family_id}")
    family=FAMILIES[family_id]
    if adaptation=="original": return family.original_provider
    if adaptation=="finetuned" and family.finetuned_provider:return family.finetuned_provider
    raise ValueError(f"{family.label} no admite la condición {adaptation} en esta plataforma")

def validate_condition(family_id:str,adaptation:str,instructional_condition:str,retrieval_method:str)->None:
    resolve_provider(family_id,adaptation)
    if instructional_condition not in {"raw","pedagogical_prompt","instructional_database"}: raise ValueError("Condición instruccional desconocida")
    if instructional_condition!="instructional_database" and retrieval_method!="none": raise ValueError("La recuperación solo se aplica con la base instruccional")
    if instructional_condition=="instructional_database" and retrieval_method not in {"rag","graph_rag","pep_sa_rag","pep_plan_rag"}: raise ValueError("Seleccione un retriever para la base instruccional")
