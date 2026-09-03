from __future__ import annotations
import pickle
from ai_tutor.embeddings.encoder import HashingEncoder
from ai_tutor.indexing.faiss_index import DenseIndex
from ai_tutor.indexing.bm25_index import BM25Index
from ai_tutor.utils.io import read_jsonl
from ai_tutor.utils.paths import load_config,project_path
from .rag import RAGRetriever
from .graph_rag import GraphRAGRetriever
from .pep_sa_rag import PEPSARAGRetriever
from .pep_plan_rag import PEPPlanRAGRetriever

def load_retriever(method:str,overrides:dict=None):
    if method not in {"rag","graph_rag","pep_sa_rag","pep_plan_rag"}: raise ValueError(f"Unknown method: {method}")
    cfg=load_config(method)
    if overrides:
        def merge(target, extra):
            for key,value in extra.items():
                if isinstance(value,dict) and isinstance(target.get(key),dict): merge(target[key],value)
                else: target[key]=value
        merge(cfg,overrides)
    paths=cfg["paths"]; chunks=read_jsonl(project_path(paths["chunks"]))
    if not chunks: raise FileNotFoundError("Run python scripts/build_dataset.py first")
    encoder=HashingEncoder(cfg["embedding"]["dimensions"]); artifact_path=project_path(paths["indexes"])
    if artifact_path.exists():
        with artifact_path.open("rb") as handle: artifact=pickle.load(handle)
        dense,sparse=artifact["dense"],artifact["bm25"]
    else:
        vectors=encoder.encode([c["text"] for c in chunks]); ids=[c["chunk_id"] for c in chunks]
        dense,sparse=DenseIndex(vectors,ids),BM25Index([c["text"] for c in chunks],ids)
    baseline=RAGRetriever(chunks,encoder,dense,sparse,{**cfg.get("retrieval",{}),**cfg})
    if method=="rag": return baseline
    with project_path(paths["graph"]).open("rb") as handle: graph=pickle.load(handle)
    if method=="graph_rag": return GraphRAGRetriever(baseline,graph,cfg)
    if method=="pep_sa_rag": return PEPSARAGRetriever(baseline,graph,cfg)
    concepts=read_jsonl(project_path(paths["concepts"]))
    units=read_jsonl(project_path(paths["instructional_units"]))
    return PEPPlanRAGRetriever(baseline,graph,concepts,units,cfg)
