from __future__ import annotations
from time import perf_counter
from .base import RetrievalResult,RetrievedChunk
from .fusion import reciprocal_rank_fusion
from ai_tutor.indexing.bm25_index import tokenize

_STOPWORDS = {"a", "al", "el", "la", "las", "los", "de", "del", "en", "un", "una", "y", "que", "como"}

class RAGRetriever:
    name="rag"
    def __init__(self,chunks,encoder,dense_index,bm25_index,config=None):
        self.chunks={c["chunk_id"]:c for c in chunks}; self.encoder=encoder; self.dense=dense_index; self.sparse=bm25_index; self.config=config or {}
    def retrieve(self,query:str,top_k:int=5,**kwargs)->RetrievalResult:
        start=perf_counter(); pool=max(top_k*4,20); q=self.encoder.encode([query])[0]
        dense=self.dense.search(q,pool) if self.config.get("use_dense",True) else []
        sparse=self.sparse.search(query,pool) if self.config.get("use_sparse",True) else []
        rankings=[]; weights=[]
        if dense: rankings.append(dense); weights.append(self.config.get("dense_weight",1))
        if sparse: rankings.append(sparse); weights.append(self.config.get("sparse_weight",1))
        if not rankings: raise ValueError("At least one of use_dense/use_sparse must be enabled")
        fused=reciprocal_rank_fusion(rankings,self.config.get("rrf_k",60),weights)
        type_weights=self.config.get("chunk_type_weights",{})
        fused=[(cid,score*type_weights.get(self.chunks[cid].get("chunk_type","other"),1.0)) for cid,score in fused]
        # Hashing embeddings are intentionally reproducible/offline but can
        # collide on short Spanish queries. Add a bounded lexical agreement
        # term so evidence that actually contains the requested topic wins
        # over an unrelated dense collision.
        query_terms = {term for term in tokenize(query) if len(term) >= 2 and term not in _STOPWORDS}
        lexical_weight = float(self.config.get("lexical_weight", 0.45))
        max_fused = max((score for _, score in fused), default=1.0) or 1.0
        rescored = []
        for cid, score in fused:
            document_terms = set(tokenize(self.chunks[cid]["text"]))
            lexical = len(query_terms & document_terms) / max(len(query_terms), 1)
            normalized_fused = score / max_fused
            rescored.append((cid, (1 - lexical_weight) * normalized_fused + lexical_weight * lexical))
        fused=sorted(rescored,key=lambda item:(-item[1],item[0]))[:top_k]
        out=[]
        for cid,score in fused:
            c=self.chunks[cid]; out.append(RetrievedChunk(cid,c["text"],score,c.get("concept_ids",[]),c))
        concepts=list(dict.fromkeys(x for c in out for x in c.concept_ids)); latency=(perf_counter()-start)*1000
        return RetrievalResult(query,out,concepts,[c.score for c in out],{"method":self.name},latency,{"dense_ranking":dense,"sparse_ranking":sparse,"fused_ranking":fused,"retrieval_latency_ms":latency})
