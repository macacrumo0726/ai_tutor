from __future__ import annotations
from typing import Optional

def reciprocal_rank_fusion(rankings:list[list[tuple[str,float]]],k:int=60,weights:Optional[list[float]]=None)->list[tuple[str,float]]:
    weights=weights or [1.0]*len(rankings); scores={}
    for ranking,weight in zip(rankings,weights):
        for rank,(ident,_) in enumerate(ranking,1): scores[ident]=scores.get(ident,0.0)+weight/(k+rank)
    return sorted(scores.items(),key=lambda x:(-x[1],x[0]))
