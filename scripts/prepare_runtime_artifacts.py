#!/usr/bin/env python3
"""Prepare the minimum corpus and graph required by the web image.

The full local corpus and binary indexes are intentionally ignored by Git.
During a cloud build, this script reuses them when supplied by the build
context. When they are absent, it creates a small deterministic runtime corpus
from the tracked instructional database so the service still starts and
answers rather than failing on its first chat request.
"""
from __future__ import annotations

import pickle

from ai_tutor.embeddings.encoder import HashingEncoder
from ai_tutor.graph.builder import build_pedagogical_graph
from ai_tutor.indexing.bm25_index import BM25Index
from ai_tutor.indexing.faiss_index import DenseIndex
from ai_tutor.utils.io import read_jsonl, write_jsonl
from ai_tutor.utils.paths import load_config, project_path


def _runtime_chunks(concepts, units):
    chunks = []
    for concept in concepts:
        text = (concept.get("description") or "").strip()
        if not text:
            unit = next((item for item in units if item.get("concept_id") == concept["concept_id"]), {})
            text = (unit.get("concept_explanation") or unit.get("learning_objective") or "").strip()
        if not text:
            continue
        chunks.append({
            "chunk_id": f"runtime_{concept['concept_id']}",
            "text": text[:12000],
            "page_start": min(concept.get("source_pages") or [0]),
            "page_end": max(concept.get("source_pages") or [0]),
            "section": concept.get("subtopic", ""),
            "topic": concept.get("topic", ""),
            "subtopic": concept.get("subtopic", ""),
            "concept_ids": [concept["concept_id"]],
            "difficulty": concept.get("difficulty", "mixed"),
            "chunk_type": "explanation",
            "source": "instructional_database_runtime_fallback",
        })
    return chunks


def main():
    cfg = load_config()
    paths = cfg["paths"]
    chunks_path = project_path(paths["chunks"])
    concepts = read_jsonl(project_path(paths["concepts"]))
    units = read_jsonl(project_path(paths["instructional_units"]))
    chunks = read_jsonl(chunks_path)
    if not chunks:
        chunks = _runtime_chunks(concepts, units)
        chunks_path.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(chunks_path, chunks)
        print(f"runtime_chunks={len(chunks)} source=tracked_instructional_database")
    else:
        print(f"runtime_chunks={len(chunks)} source=provided_corpus")

    index_path = project_path(paths["indexes"])
    graph_path = project_path(paths["graph"])
    if not index_path.exists():
        encoder = HashingEncoder(cfg["embedding"]["dimensions"])
        texts = [item["text"] for item in chunks]
        ids = [item["chunk_id"] for item in chunks]
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with index_path.open("wb") as handle:
            pickle.dump({
                "dense": DenseIndex(encoder.encode(texts), ids),
                "bm25": BM25Index(texts, ids),
                "embedding": cfg["embedding"],
                "chunk_ids": ids,
            }, handle)
        print(f"runtime_indexes={len(ids)}")

    if not graph_path.exists():
        relations = read_jsonl(project_path(paths["relations"]))
        questions_path = project_path(paths["questions"])
        questions = read_jsonl(questions_path) if questions_path.exists() else []
        graph = build_pedagogical_graph(concepts, chunks, units, questions, relations)
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        with graph_path.open("wb") as handle:
            pickle.dump(graph, handle)
        print(f"runtime_graph_nodes={graph.number_of_nodes()} edges={graph.number_of_edges()}")


if __name__ == "__main__":
    main()
