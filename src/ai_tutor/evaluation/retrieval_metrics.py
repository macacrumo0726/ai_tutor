from __future__ import annotations
import math

NOT_AVAILABLE="not_available"
def _available(gold): return gold is not None and len(gold)>0
def hit_at_k(retrieved,gold,k): return NOT_AVAILABLE if not _available(gold) else float(bool(set(retrieved[:k])&set(gold)))
def recall_at_k(retrieved,gold,k): return NOT_AVAILABLE if not _available(gold) else len(set(retrieved[:k])&set(gold))/len(set(gold))
def mrr_at_k(retrieved,gold,k):
    if not _available(gold): return NOT_AVAILABLE
    return next((1/i for i,x in enumerate(retrieved[:k],1) if x in set(gold)),0.0)
def ndcg_at_k(retrieved,gold,k):
    if not _available(gold): return NOT_AVAILABLE
    gains=[1.0 if x in set(gold) else 0.0 for x in retrieved[:k]]
    dcg=sum(g/math.log2(i+2) for i,g in enumerate(gains)); ideal=sum(1/math.log2(i+2) for i in range(min(k,len(set(gold)))))
    return dcg/ideal if ideal else 0.0
def concept_recall(retrieved,gold): return recall_at_k(retrieved,gold,len(retrieved))
def prerequisite_recall(retrieved,gold): return recall_at_k(retrieved,gold,len(retrieved))

