#!/usr/bin/env python3
from __future__ import annotations
import pickle
from ai_tutor.embeddings.encoder import HashingEncoder
from ai_tutor.indexing.bm25_index import BM25Index
from ai_tutor.indexing.faiss_index import DenseIndex
from ai_tutor.utils.io import read_jsonl
from ai_tutor.utils.paths import load_config,project_path

def main():
    cfg=load_config(); chunks=read_jsonl(project_path(cfg["paths"]["chunks"]))
    if not chunks: raise SystemExit("Run build_dataset.py first")
    enc=HashingEncoder(cfg["embedding"]["dimensions"]); texts=[c["text"] for c in chunks]; ids=[c["chunk_id"] for c in chunks]
    artifact={"dense":DenseIndex(enc.encode(texts),ids),"bm25":BM25Index(texts,ids),"embedding":cfg["embedding"],"chunk_ids":ids}
    path=project_path(cfg["paths"]["indexes"]); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("wb") as handle: pickle.dump(artifact,handle)
    print(f"indexed={len(ids)} path={path}")
if __name__=="__main__": main()

