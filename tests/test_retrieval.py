from ai_tutor.retrieval.fusion import reciprocal_rank_fusion
from ai_tutor.retrieval.graph_rag import GraphRAGRetriever
from ai_tutor.retrieval.pep_sa_rag import PEPSARAGRetriever

def test_rrf_rewards_items_in_both_rankings():
    result=reciprocal_rank_fusion([[('a',1),('b',.5)],[('b',2),('c',1)]],k=60)
    assert result[0][0]=="b"

def test_baseline_common_result_shape(baseline):
    result=baseline.retrieve("dominio racional",2)
    assert result.metadata["method"]=="rag" and len(result.chunks)==2

def test_graph_expansion_is_bounded(baseline,graph):
    retriever=GraphRAGRetriever(baseline,graph,{"max_hops":2,"max_nodes":2,"max_neighbors_per_node":2,"use_prerequisites":True,"use_neighbors":True,"use_ppr":False})
    expanded,_,prerequisites=retriever._expand(["quadratic"])
    assert len(expanded)<=2 and "factorization" in expanded and "factorization" in prerequisites

def test_pep_sa_v2_reports_reranking_and_context_quotas(baseline,graph):
    retriever=PEPSARAGRetriever(baseline,graph,{"pep_version":"v2","max_hops":2,"max_nodes":10,"max_iterations":3,"query_restart":.2,"direct_evidence_quota":1,"prerequisite_evidence_quota":1,"instructional_evidence_quota":0,"adaptive_context_quotas":False})
    result=retriever.retrieve("ecuación cuadrática",2)
    assert result.debug_info["pep_version"]=="v2"
    assert result.debug_info["context_quotas"]=={"direct":1,"prerequisite":1,"instructional":0}
    assert result.debug_info["rerank_contributions"]
