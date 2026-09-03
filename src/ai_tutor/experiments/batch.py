from __future__ import annotations
import csv
import json
import random
import statistics
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

from ai_tutor.evaluation.retrieval_metrics import (
    hit_at_k,recall_at_k,mrr_at_k,ndcg_at_k,concept_recall,prerequisite_recall,
)
from ai_tutor.retrieval.factory import load_retriever

METHOD_SPECS={
    "rag":("rag",{}),
    "graph_rag":("graph_rag",{}),
    "pep_sa_rag_v1":("pep_sa_rag",{"pep_version":"v1","query_restart":0.0,"forward_successor_weight":0.0,"ranking_stability_patience":0}),
    "pep_sa_rag_v2":("pep_sa_rag",{}),
    "pep_plan_rag_v3":("pep_plan_rag",{}),
}
METHODS=tuple(METHOD_SPECS)
ABLATIONS={
    "dense_only":("rag",{"use_dense":True,"use_sparse":False}),
    "bm25_only":("rag",{"use_dense":False,"use_sparse":True}),
    "dense_bm25_rrf":("rag",{"use_dense":True,"use_sparse":True}),
    "graph_neighbors":("graph_rag",{"use_neighbors":True,"use_prerequisites":False,"use_ppr":False}),
    "graph_prerequisites":("graph_rag",{"use_neighbors":False,"use_prerequisites":True,"use_ppr":False}),
    "graph_ppr":("graph_rag",{"use_neighbors":True,"use_prerequisites":True,"use_ppr":True}),
    "pep_sa_v1":("pep_sa_rag",{"pep_version":"v1","query_restart":0.0,"forward_successor_weight":0.0,"ranking_stability_patience":0}),
    "pep_sa_v2_no_restart":("pep_sa_rag",{"query_restart":0.0}),
    "pep_sa_v2_no_quotas":("pep_sa_rag",{"direct_evidence_quota":5,"prerequisite_evidence_quota":0,"instructional_evidence_quota":0,"adaptive_context_quotas":False}),
    "pep_sa_v2_uniform_weights":("pep_sa_rag",{"prerequisite_weight":0.45,"related_weight":0.45}),
    "pep_sa_v2_direct4_uniform":("pep_sa_rag",{"prerequisite_weight":0.45,"related_weight":0.45,"direct_evidence_quota":4,"prerequisite_evidence_quota":1,"instructional_evidence_quota":0,"adaptive_context_quotas":False}),
    "pep_sa_v2_noquotas_uniform":("pep_sa_rag",{"prerequisite_weight":0.45,"related_weight":0.45,"direct_evidence_quota":5,"prerequisite_evidence_quota":0,"instructional_evidence_quota":0,"adaptive_context_quotas":False}),
    "pep_sa_v2_full":("pep_sa_rag",{}),
    "pep_plan_v3_no_student_gap":("pep_plan_rag",{"utility_weights":{"student_gap":0.0}}),
    "pep_plan_v3_no_activation":("pep_plan_rag",{"utility_weights":{"activation":0.0}}),
    "pep_plan_v3_no_prerequisite_utility":("pep_plan_rag",{"utility_weights":{"prerequisite_need":0.0}}),
    "pep_plan_v3_no_diversity":("pep_plan_rag",{"redundancy_weight":0.0}),
    "pep_plan_v3_full":("pep_plan_rag",{}),
}

def retrieval_row(question:dict,label:str,retriever,top_k:int,variant="original",query=None)->dict:
    result=retriever.retrieve(query or question["question"],top_k)
    chunks=[c.chunk_id for c in result.chunks]; concepts=result.concepts
    activated_prereqs=result.debug_info.get("prerequisites_activated",[])
    prerequisite_candidates=list(dict.fromkeys(concepts+activated_prereqs))
    return {
        "question_id":question["question_id"],"method":label,"variant":variant,
        "question_type":question.get("question_type","unknown"),"difficulty":question.get("difficulty","unknown"),
        "requires_prerequisites":bool(question.get("gold_prerequisite_ids")),
        "retrieved_chunk_ids":chunks,"retrieved_concept_ids":concepts,"retrieved_prerequisite_ids":activated_prereqs,
        "hit_at_k":hit_at_k(chunks,question.get("gold_chunk_ids"),top_k),
        "recall_at_k":recall_at_k(chunks,question.get("gold_chunk_ids"),top_k),
        "mrr":mrr_at_k(chunks,question.get("gold_chunk_ids"),top_k),
        "ndcg_at_k":ndcg_at_k(chunks,question.get("gold_chunk_ids"),top_k),
        "concept_recall":concept_recall(concepts,question.get("gold_concept_ids")),
        "prerequisite_recall":prerequisite_recall(prerequisite_candidates,question.get("gold_prerequisite_ids")),
        "latency_ms":result.latency_ms,"nodes_visited":result.debug_info.get("nodes_visited",len(result.debug_info.get("expanded_nodes",[]))),
        "edges_visited":result.debug_info.get("edges_visited",len(result.debug_info.get("edges_used",[]))),
        "iterations":result.debug_info.get("iterations",0),
    }

def robust_queries(question:str)->dict:
    informal=question.lower().replace("¿","").replace("?","")
    return {"original":question,"polite":f"¿Podrías ayudarme a entender lo siguiente: {question}","informal":f"no entiendo {informal}, me ayudas?"}

def mean_available(values):
    numeric=[float(v) for v in values if isinstance(v,(int,float)) and not isinstance(v,bool)]
    return round(statistics.fmean(numeric),6) if numeric else "not_available"

def bootstrap_ci(values,seed=42,resamples=1000):
    values=[float(v) for v in values if isinstance(v,(int,float)) and not isinstance(v,bool)]
    if not values:return ["not_available","not_available"]
    rng=random.Random(seed); means=[]; n=len(values)
    for _ in range(resamples):means.append(statistics.fmean(rng.choice(values) for _ in range(n)))
    means.sort(); return [round(means[int(.025*(resamples-1))],6),round(means[int(.975*(resamples-1))],6)]

def summarize(rows:list[dict],group_key="method",seed=42)->list[dict]:
    groups=defaultdict(list)
    for row in rows:groups[str(row[group_key])].append(row)
    metrics=("hit_at_k","recall_at_k","mrr","ndcg_at_k","concept_recall","prerequisite_recall","latency_ms","nodes_visited","edges_visited","iterations")
    output=[]
    for name,items in sorted(groups.items()):
        summary={group_key:name,"n":len(items)}
        for metric in metrics:
            values=[r.get(metric) for r in items]; summary[metric]=mean_available(values)
            if metric in {"hit_at_k","concept_recall","prerequisite_recall","latency_ms"}:summary[f"{metric}_ci95"]=bootstrap_ci(values,seed)
        output.append(summary)
    return output

def summarize_generation(rows:list[dict],seed=42)->list[dict]:
    groups=defaultdict(list)
    for row in rows:
        if "condition" in row:groups[row["condition"]].append(row)
    metrics=("exact_match","token_f1","retrieval_hit","concept_recall","prerequisite_recall","latency_ms","generation_latency_ms","retrieval_latency_ms")
    output=[]
    for condition,items in sorted(groups.items()):
        row={"condition":condition,"n":len(items),"errors":sum("error" in item for item in items)}
        for metric in metrics:
            row[metric]=mean_available([item.get(metric) for item in items])
            if metric in {"token_f1","concept_recall","prerequisite_recall","latency_ms"}:row[f"{metric}_ci95"]=bootstrap_ci([item.get(metric) for item in items],seed)
        output.append(row)
    return output

def write_blinded_rubric(run_dir:Path,rows:list[dict],seed=42):
    rng=random.Random(seed); evaluable=[r for r in rows if "answer" in r]; rng.shuffle(evaluable)
    rubric=[]; mapping=[]
    for index,row in enumerate(evaluable,1):
        response_id=f"response_{index:05d}"
        rubric.append({"response_id":response_id,"question":row["question"],"answer":row["answer"],
            "recognition_of_difficulty":"not_rated","prior_knowledge_activation":"not_rated","scaffolding":"not_rated",
            "micro_checks":"not_rated","pedagogical_coherence":"not_rated","answer_correctness":"not_rated","reviewer_notes":""})
        mapping.append({"response_id":response_id,"question_id":row["question_id"],"condition":row["condition"]})
    write_csv(run_dir/"human_rubric_blinded.csv",rubric); write_csv(run_dir/"human_rubric_key.csv",mapping)

def write_csv(path:Path,rows:list[dict]):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:return
    fields=list(rows[0])
    with path.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader()
        for row in rows:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()})

def run_retrieval(questions,top_k=5):
    retrievers={label:load_retriever(method,overrides) for label,(method,overrides) in METHOD_SPECS.items()}
    return [retrieval_row(q,m,retrievers[m],top_k) for q in questions for m in METHODS]

def run_ablations(questions,top_k=5):
    retrievers={name:load_retriever(method,overrides) for name,(method,overrides) in ABLATIONS.items()}
    return [retrieval_row(q,name,retrievers[name],top_k) for q in questions for name in ABLATIONS]

def run_robustness(questions,top_k=5):
    retrievers={label:load_retriever(method,overrides) for label,(method,overrides) in METHOD_SPECS.items()}; rows=[]
    for question in questions:
        for variant,query in robust_queries(question["question"]).items():
            for method,retriever in retrievers.items():rows.append(retrieval_row(question,method,retriever,top_k,variant,query))
    return rows

def manifest(config:dict)->dict:
    return {"created_at":datetime.now(timezone.utc).isoformat(),**config}
