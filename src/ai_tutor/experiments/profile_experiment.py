from __future__ import annotations

from collections import defaultdict
import statistics

from ai_tutor.evaluation.retrieval_metrics import (
    concept_recall, hit_at_k, ndcg_at_k, prerequisite_recall, recall_at_k,
)
from ai_tutor.student_model import StudentState


METHODS=("rag","graph_rag","pep_plan_rag")
PROFILES=("unknown","high_prerequisite_mastery","prerequisite_gap")


def simulated_profiles(question):
    prerequisites=list(question.get("gold_prerequisite_ids") or [])
    target=list(question.get("gold_concept_ids") or [])
    return {
        "unknown":StudentState("unknown",default_mastery=.50,confidence=0),
        "high_prerequisite_mastery":StudentState(
            "high_prerequisite_mastery",default_mastery=.80,
            concept_mastery={concept:.90 for concept in prerequisites+target},
            confidence=.90,evidence_count=8),
        "prerequisite_gap":StudentState(
            "prerequisite_gap",default_mastery=.60,
            concept_mastery={**{concept:.10 for concept in prerequisites},
                             **{concept:.55 for concept in target}},
            confidence=.90,evidence_count=8),
    }


def evaluate_profile_case(question,method,profile_name,profile,retriever,top_k=5):
    # RAG and Graph-RAG receive the same argument deliberately: invariance is a
    # control condition, not an implementation shortcut.
    result=retriever.retrieve(question["question"],top_k,student_profile=profile,
                              student_state=profile)
    chunk_ids=[chunk.chunk_id for chunk in result.chunks]
    concepts=list(result.concepts)
    activated=list(result.debug_info.get("prerequisites_activated",[]))
    available_prerequisites=list(dict.fromkeys(concepts+activated))
    gold_prerequisites=question.get("gold_prerequisite_ids") or []
    prerequisite_chunk_count=sum(
        bool(set(chunk.concept_ids)&set(gold_prerequisites)) for chunk in result.chunks)
    return {
        "question_id":question["question_id"],"method":method,"profile":profile_name,
        "question_type":question.get("question_type"),"chunk_ids":chunk_ids,
        "concept_ids":concepts,"activated_prerequisite_ids":activated,
        "hit_at_k":hit_at_k(chunk_ids,question.get("gold_chunk_ids"),top_k),
        "recall_at_k":recall_at_k(chunk_ids,question.get("gold_chunk_ids"),top_k),
        "ndcg_at_k":ndcg_at_k(chunk_ids,question.get("gold_chunk_ids"),top_k),
        "concept_recall":concept_recall(concepts,question.get("gold_concept_ids")),
        "prerequisite_recall":prerequisite_recall(
            available_prerequisites,gold_prerequisites),
        "prerequisite_context_share":prerequisite_chunk_count/max(1,len(result.chunks)),
        "latency_ms":result.latency_ms,
        "planned_missing_prerequisites":result.debug_info.get("learning_path",{}).get(
            "missing_prerequisites",[]),
    }


def _mean(rows,key):
    values=[float(row[key]) for row in rows if isinstance(row.get(key),(int,float))]
    return round(statistics.fmean(values),6) if values else "not_available"


def summarize_profile_rows(rows):
    groups=defaultdict(list)
    for row in rows: groups[(row["method"],row["profile"])].append(row)
    metrics=("hit_at_k","recall_at_k","ndcg_at_k","concept_recall",
             "prerequisite_recall","prerequisite_context_share","latency_ms")
    return [{"method":method,"profile":profile,"n":len(items),
             **{metric:_mean(items,metric) for metric in metrics}}
            for (method,profile),items in sorted(groups.items())]


def counterfactual_summary(rows):
    indexed={(row["question_id"],row["method"],row["profile"]):row for row in rows}
    output=[]
    for method in METHODS:
        pairs=[]
        question_ids=sorted({row["question_id"] for row in rows if row["method"]==method})
        for question_id in question_ids:
            high=indexed.get((question_id,method,"high_prerequisite_mastery"))
            gap=indexed.get((question_id,method,"prerequisite_gap"))
            if not high or not gap: continue
            high_chunks=set(high["chunk_ids"]); gap_chunks=set(gap["chunk_ids"])
            union=high_chunks|gap_chunks
            pairs.append({
                "chunk_jaccard_distance":1-len(high_chunks&gap_chunks)/max(1,len(union)),
                "prerequisite_recall_lift":float(gap["prerequisite_recall"])-float(high["prerequisite_recall"]),
                "prerequisite_context_lift":gap["prerequisite_context_share"]-high["prerequisite_context_share"],
                "target_recall_cost":float(high["concept_recall"])-float(gap["concept_recall"]),
            })
        output.append({"method":method,"paired_questions":len(pairs),
                       **{key:_mean(pairs,key) for key in (
                           "chunk_jaccard_distance","prerequisite_recall_lift",
                           "prerequisite_context_lift","target_recall_cost")}})
    return output
