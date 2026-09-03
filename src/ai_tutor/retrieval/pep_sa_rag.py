from __future__ import annotations
from time import perf_counter
from .base import RetrievalResult,RetrievedChunk
from ai_tutor.graph.spreading_activation import spread_activation

class PEPSARAGRetriever:
    name="pep_sa_rag"
    def __init__(self,baseline,graph,config=None): self.baseline=baseline; self.graph=graph; self.config=config or {}
    @staticmethod
    def _normalize(values):
        maximum=max(values.values(),default=0.0)
        return {key:(value/maximum if maximum else 0.0) for key,value in values.items()}
    def _quotas(self,query,top_k):
        direct=self.config.get("direct_evidence_quota",3); prereq=self.config.get("prerequisite_evidence_quota",1)
        instructional=self.config.get("instructional_evidence_quota",1)
        if self.config.get("adaptive_context_quotas",True) and any(term in query.lower() for term in ("conocimientos previos","prerrequis","antes de aprender")):
            direct,prereq,instructional=2,2,1
        direct=min(direct,top_k); prereq=min(prereq,max(0,top_k-direct)); instructional=min(instructional,max(0,top_k-direct-prereq))
        return {"direct":direct,"prerequisite":prereq,"instructional":instructional}
    def _select_with_quotas(self,ranked,direct_ids,prereqs,top_k,query):
        quotas=self._quotas(query,top_k); selected=[]; buckets={}
        def take(label,predicate,count):
            for chunk in ranked:
                if len([x for x in selected if buckets.get(x.chunk_id)==label])>=count:break
                if chunk.chunk_id not in {x.chunk_id for x in selected} and predicate(chunk):selected.append(chunk); buckets[chunk.chunk_id]=label
        take("direct",lambda c:c.chunk_id in direct_ids,quotas["direct"])
        take("prerequisite",lambda c:any(x in prereqs for x in c.concept_ids),quotas["prerequisite"])
        instructional_types={"definition","explanation","worked_example","example"}
        take("instructional",lambda c:c.metadata.get("chunk_type") in instructional_types,quotas["instructional"])
        for chunk in ranked:
            if len(selected)>=top_k:break
            if chunk.chunk_id not in {x.chunk_id for x in selected}:selected.append(chunk); buckets[chunk.chunk_id]="fill"
        return selected[:top_k],quotas,buckets
    def retrieve(self,query:str,top_k:int=5,**kwargs)->RetrievalResult:
        start=perf_counter(); base=self.baseline.retrieve(query,max(top_k*3,10)); graph_start=perf_counter()
        seed_scores={c:1/(i+1) for i,c in enumerate(base.concepts)}
        activation=spread_activation(self.graph,seed_scores,self.config); dynamics_ms=(perf_counter()-graph_start)*1000
        candidates={c.chunk_id:c for c in base.chunks}; direct_ids=set(candidates)
        for concept,value in activation.final.items():
            for _,node,data in self.graph.out_edges(concept,data=True):
                if data.get("edge_type")=="EXPLAINS" and node.startswith("chunk::"):
                    cid=node.split("::",1)[1]; raw=self.baseline.chunks.get(cid)
                    if raw and cid not in candidates: candidates[cid]=RetrievedChunk(cid,raw["text"],0.0,raw.get("concept_ids",[]),raw)
        rerank=perf_counter()
        version=self.config.get("pep_version","v2"); population=set(activation.final)|set(seed_scores)
        prerequisite_targets=set(seed_scores) if version=="v1" else population
        prereqs=[c for c in activation.final if any(d.get("edge_type")=="PREREQUISITE_OF" and t in prerequisite_targets for _,t,d in self.graph.out_edges(c,data=True))]
        contributions={}
        if version=="v1":
            weight=self.config.get("graph_weight",.4)
            for chunk in candidates.values():chunk.score+=weight*sum(activation.final.get(c,0) for c in chunk.concept_ids)
            chunks=sorted(candidates.values(),key=lambda c:(-c.score,c.chunk_id))[:top_k]; quotas={}; buckets={}
        else:
            direct_raw={cid:chunk.score if cid in direct_ids else 0.0 for cid,chunk in candidates.items()}
            activation_raw={cid:sum(activation.final.get(c,0) for c in chunk.concept_ids) for cid,chunk in candidates.items()}
            direct_norm=self._normalize(direct_raw); activation_norm=self._normalize(activation_raw)
            dw=self.config.get("direct_relevance_weight",.60); aw=self.config.get("activation_rerank_weight",.20)
            pw=self.config.get("prerequisite_utility_weight",.10); iw=self.config.get("instructional_value_weight",.10)
            instructional_types={"definition","explanation","worked_example","example"}
            for cid,chunk in candidates.items():
                prereq_utility=float(any(c in prereqs for c in chunk.concept_ids)); instructional=float(chunk.metadata.get("chunk_type") in instructional_types)
                chunk.score=dw*direct_norm[cid]+aw*activation_norm[cid]+pw*prereq_utility+iw*instructional
                contributions[cid]={"direct":direct_norm[cid],"activation":activation_norm[cid],"prerequisite_utility":prereq_utility,"instructional_value":instructional,"final":chunk.score}
            ranked=sorted(candidates.values(),key=lambda c:(-c.score,c.chunk_id))
            chunks,quotas,buckets=self._select_with_quotas(ranked,direct_ids,set(prereqs),top_k,query)
        rerank_ms=(perf_counter()-rerank)*1000; latency=(perf_counter()-start)*1000
        debug={"pep_version":version,"initial_activation":seed_scores,"final_activation":activation.final,"activation_history":activation.history,"iterations":activation.iterations,"activated_concepts":list(activation.final),"prerequisites_activated":prereqs,"nodes_visited":activation.nodes_visited,"edges_visited":activation.edges_visited,"retrieval_latency_ms":latency,"graph_latency_ms":dynamics_ms,"population_dynamics_latency_ms":dynamics_ms,"reranking_latency_ms":rerank_ms,"rerank_contributions":contributions,"context_quotas":quotas,"context_buckets":buckets,"final_chunks":[c.chunk_id for c in chunks]}
        return RetrievalResult(query,chunks,list(dict.fromkeys(x for c in chunks for x in c.concept_ids)),[c.score for c in chunks],{"method":self.name},latency,debug)
