from __future__ import annotations
from time import perf_counter
import networkx as nx
from .base import RetrievalResult,RetrievedChunk
from ai_tutor.graph.pagerank import personalized_pagerank

class GraphRAGRetriever:
    name="graph_rag"
    def __init__(self,baseline,graph:nx.DiGraph,config=None): self.baseline=baseline; self.graph=graph; self.config=config or {}
    def _expand(self,seeds):
        visited=set(seeds); frontier=list(seeds); used=[]; prerequisites=set()
        max_nodes=self.config.get("max_nodes",80); limit=self.config.get("max_neighbors_per_node",12)
        for _ in range(self.config.get("max_hops",2)):
            nxt=[]
            for node in frontier:
                candidates=[]
                if self.config.get("use_neighbors",True): candidates.extend(self.graph.successors(node))
                incoming_prereqs=[s for s,_,d in self.graph.in_edges(node,data=True) if d.get("edge_type")=="PREREQUISITE_OF"]
                if self.config.get("use_prerequisites",True):candidates.extend(incoming_prereqs)
                for target in list(dict.fromkeys(candidates))[:limit]:
                    if target not in visited and self.graph.nodes[target].get("node_type")=="Concept":
                        visited.add(target); nxt.append(target); used.append((node,target));
                        if target in incoming_prereqs:prerequisites.add(target)
                        if len(visited)>=max_nodes: return visited,used,prerequisites
            frontier=nxt
        return visited,used,prerequisites
    def retrieve(self,query:str,top_k:int=5,**kwargs)->RetrievalResult:
        start=perf_counter(); seed_result=self.baseline.retrieve(query,max(top_k*3,10)); seeds=seed_result.concepts
        expanded,edges,prerequisites=self._expand(seeds); ppr={}
        if self.config.get("use_ppr",True):
            concept_graph=self.graph.subgraph([n for n in expanded if n in self.graph]).copy(); ppr=personalized_pagerank(concept_graph,seeds,self.config.get("ppr_alpha",.85))
        candidates={c.chunk_id:c for c in seed_result.chunks}
        for concept in expanded:
            for _,node,data in self.graph.out_edges(concept,data=True):
                if data.get("edge_type")=="EXPLAINS" and node.startswith("chunk::"):
                    cid=node.split("::",1)[1]; raw=self.baseline.chunks.get(cid)
                    if raw and cid not in candidates: candidates[cid]=RetrievedChunk(cid,raw["text"],0.0,raw.get("concept_ids",[]),raw)
        weight=self.config.get("graph_weight",.35)
        for chunk in candidates.values(): chunk.score += weight*sum(ppr.get(c,0) for c in chunk.concept_ids)
        chunks=sorted(candidates.values(),key=lambda c:(-c.score,c.chunk_id))[:top_k]; latency=(perf_counter()-start)*1000
        debug={"seed_chunks":[c.chunk_id for c in seed_result.chunks],"seed_concepts":seeds,"expanded_nodes":sorted(expanded),"edges_used":edges,"prerequisites_activated":sorted(prerequisites),"ppr_scores":ppr,"final_chunks":[c.chunk_id for c in chunks],"retrieval_latency_ms":latency}
        return RetrievalResult(query,chunks,list(dict.fromkeys(x for c in chunks for x in c.concept_ids)),[c.score for c in chunks],{"method":self.name},latency,debug)
