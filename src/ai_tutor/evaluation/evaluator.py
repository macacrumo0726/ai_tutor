from __future__ import annotations
from datetime import datetime,timezone
import subprocess
from .answer_metrics import exact_match,token_f1
from .retrieval_metrics import hit_at_k,recall_at_k,mrr_at_k,ndcg_at_k,concept_recall,prerequisite_recall

def evaluate_one(tutor,question:dict,method:str,top_k:int,metadata:dict)->dict:
    response=tutor.ask(question["question"],method,top_k); result=response.retrieval
    chunks=[c.chunk_id for c in result.chunks]; concepts=result.concepts; prereqs=result.debug_info.get("prerequisites_activated",[])
    prerequisite_candidates=list(dict.fromkeys(concepts+prereqs))
    gold_chunks=question.get("gold_chunk_ids",[]); gold_concepts=question.get("gold_concept_ids",[]); gold_prereqs=question.get("gold_prerequisite_ids",[])
    return {**metadata,"timestamp":datetime.now(timezone.utc).isoformat(),"question_id":question["question_id"],"method":method,"question":question["question"],"answer":response.answer,"expected_answer":question["expected_answer"],"concept_id":question["concept_id"],"retrieved_chunk_ids":chunks,"retrieved_concept_ids":concepts,"required_concepts":question["required_concepts"],"required_prerequisites":question["required_prerequisites"],"exact_match":exact_match(response.answer,question["expected_answer"]),"token_f1":token_f1(response.answer,question["expected_answer"]),"retrieval_hit":hit_at_k(chunks,gold_chunks,top_k),"recall_at_k":recall_at_k(chunks,gold_chunks,top_k),"mrr":mrr_at_k(chunks,gold_chunks,top_k),"ndcg":ndcg_at_k(chunks,gold_chunks,top_k),"concept_recall":concept_recall(concepts,gold_concepts),"prerequisite_recall":prerequisite_recall(prerequisite_candidates,gold_prereqs),"latency_ms":response.total_latency_ms,"generation_latency_ms":response.generation_latency_ms,"retrieval_latency_ms":result.latency_ms,"debug_info":result.debug_info}

def evaluate_condition(tutor,question:dict,condition:str,top_k:int,metadata:dict)->dict:
    if condition in {"raw","pedagogical_prompt"}:
        knowledge_mode=condition; method="rag"
    elif condition in {"rag","graph_rag","pep_sa_rag"}:
        knowledge_mode="instructional_database"; method=condition
    else:
        raise ValueError(f"Condición experimental desconocida: {condition}")
    response=tutor.ask(question["question"],method,top_k,knowledge_mode=knowledge_mode)
    result=response.retrieval
    chunks=[c.chunk_id for c in result.chunks]; concepts=result.concepts
    prereqs=result.debug_info.get("prerequisites_activated",[])
    gold_chunks=question.get("gold_chunk_ids",[]); gold_concepts=question.get("gold_concept_ids",[])
    gold_prereqs=question.get("gold_prerequisite_ids",[])
    retrieval_available=condition not in {"raw","pedagogical_prompt"}
    return {**metadata,"timestamp":datetime.now(timezone.utc).isoformat(),"question_id":question["question_id"],
        "condition":condition,"method":method if retrieval_available else "none","knowledge_mode":knowledge_mode,
        "question":question["question"],"answer":response.answer,"expected_answer":question["expected_answer"],
        "pedagogical_trace":response.pedagogical_trace,
        "concept_id":question["concept_id"],"retrieved_chunk_ids":chunks,"retrieved_concept_ids":concepts,
        "required_concepts":question["required_concepts"],"required_prerequisites":question["required_prerequisites"],
        "exact_match":exact_match(response.answer,question["expected_answer"]),"token_f1":token_f1(response.answer,question["expected_answer"]),
        "retrieval_hit":hit_at_k(chunks,gold_chunks,top_k) if retrieval_available else "not_available",
        "recall_at_k":recall_at_k(chunks,gold_chunks,top_k) if retrieval_available else "not_available",
        "mrr":mrr_at_k(chunks,gold_chunks,top_k) if retrieval_available else "not_available",
        "ndcg":ndcg_at_k(chunks,gold_chunks,top_k) if retrieval_available else "not_available",
        "concept_recall":concept_recall(concepts,gold_concepts) if retrieval_available else "not_available",
        "prerequisite_recall":prerequisite_recall(list(dict.fromkeys(concepts+prereqs)),gold_prereqs) if retrieval_available else "not_available",
        "latency_ms":response.total_latency_ms,"generation_latency_ms":response.generation_latency_ms,
        "retrieval_latency_ms":result.latency_ms,"debug_info":result.debug_info}

def git_commit():
    try:return subprocess.check_output(["git","rev-parse","HEAD"],text=True,stderr=subprocess.DEVNULL).strip()
    except Exception:return "uncommitted"
