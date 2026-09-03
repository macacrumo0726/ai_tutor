import networkx as nx
import pytest
from ai_tutor.embeddings.encoder import HashingEncoder
from ai_tutor.indexing.faiss_index import DenseIndex
from ai_tutor.indexing.bm25_index import BM25Index
from ai_tutor.retrieval.rag import RAGRetriever

@pytest.fixture
def chunks():
    return [
      {"chunk_id":"c1","text":"Una ecuación cuadrática puede resolverse por factorización.","concept_ids":["quadratic"]},
      {"chunk_id":"c2","text":"La factorización expresa un polinomio como producto.","concept_ids":["factorization"]},
      {"chunk_id":"c3","text":"El dominio de una función racional excluye ceros del denominador.","concept_ids":["domain","rational"]},
    ]

@pytest.fixture
def baseline(chunks):
    enc=HashingEncoder(64); vectors=enc.encode([c["text"] for c in chunks]); ids=[c["chunk_id"] for c in chunks]
    return RAGRetriever(chunks,enc,DenseIndex(vectors,ids),BM25Index([c["text"] for c in chunks],ids))

@pytest.fixture
def graph(chunks):
    g=nx.DiGraph()
    for n in ["algebra","factorization","quadratic","domain","rational"]: g.add_node(n,node_type="Concept")
    g.add_edge("algebra","factorization",edge_type="PREREQUISITE_OF",weight=1)
    g.add_edge("factorization","quadratic",edge_type="PREREQUISITE_OF",weight=1)
    for c in chunks:
      node="chunk::"+c["chunk_id"]; g.add_node(node,node_type="Chunk")
      for concept in c["concept_ids"]: g.add_edge(concept,node,edge_type="EXPLAINS",weight=1)
    return g

