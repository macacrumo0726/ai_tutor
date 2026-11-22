#!/usr/bin/env python3
"""Compare LLM provider architectures while keeping PEP-Plan-RAG v3 fixed."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from ai_tutor.evaluation.evaluator import evaluate_one, git_commit
from ai_tutor.tutoring.tutor import Tutor
from ai_tutor.utils.io import read_jsonl
from ai_tutor.utils.paths import load_config, project_path


ARCHITECTURES = {
    "gpt_primary": ["openai"],
    "deepseek_primary": ["deepseek", "instructional"],
    "qwen_primary_deepseek_fallback": ["local_qwen3_1_7b", "deepseek", "openai", "instructional"],
    "phi4_primary_deepseek_fallback": ["local_phi4_mini", "deepseek", "openai", "instructional"],
    "gpt_primary_deepseek_fallback": ["openai", "deepseek", "instructional"],
}


def run(args):
    cfg = load_config()
    questions = [q for q in read_jsonl(project_path(args.dataset or cfg["paths"]["questions"]))
                 if args.split == "all" or q.get("split") == args.split]
    questions = questions[:args.limit] if args.limit else questions
    selected = args.architectures or list(ARCHITECTURES)
    metadata = {
        "experiment_id": "llm-architectures-pep-v3-v1",
        "git_commit": git_commit(),
        "split": args.split,
        "dataset_version": cfg["project"]["dataset_version"],
        "embedding_model": cfg["embedding"]["model"],
        "retrieval_method": "pep_plan_rag",
        "top_k": args.top_k,
    }
    tutors = {}
    rows = []
    for architecture in selected:
        providers = ARCHITECTURES[architecture]
        for question in questions:
            started = time.perf_counter()
            response = None
            errors = []
            used_provider = None
            for provider in providers:
                try:
                    tutor = tutors.setdefault(provider, Tutor(generator_provider=provider))
                    candidate = tutor.ask(question["question"], "pep_plan_rag", args.top_k,
                                          knowledge_mode="instructional_database")
                    if candidate.generation_error or not candidate.answer.strip():
                        errors.append(f"{provider}: {candidate.generation_error or 'empty'}")
                        continue
                    response, used_provider = candidate, provider
                    break
                except Exception as exc:
                    errors.append(f"{provider}: {exc}")
            if response is None:
                rows.append({**metadata, "architecture": architecture,
                             "question_id": question["question_id"], "question": question["question"],
                             "status": "failed", "errors": errors,
                             "latency_ms": round((time.perf_counter() - started) * 1000, 2)})
                continue
            # Reuse the common evaluation metrics for the selected response.
            # The response was already generated; this second call is avoided
            # by extracting the same fields directly.
            result = response.retrieval
            chunks = [c.chunk_id for c in result.chunks]
            concepts = list(result.concepts)
            from ai_tutor.evaluation.answer_metrics import exact_match, token_f1
            from ai_tutor.evaluation.retrieval_metrics import hit_at_k, concept_recall, prerequisite_recall
            gold_chunks = question.get("gold_chunk_ids", [])
            gold_concepts = question.get("gold_concept_ids", [])
            gold_prereqs = question.get("gold_prerequisite_ids", [])
            prereqs = result.debug_info.get("prerequisites_activated", [])
            rows.append({**metadata, "architecture": architecture,
                         "question_id": question["question_id"], "question": question["question"],
                         "answer": response.answer, "status": "ok", "provider": used_provider,
                         "fallback_used": used_provider != providers[0], "errors": errors,
                         "exact_match": exact_match(response.answer, question["expected_answer"]),
                         "token_f1": token_f1(response.answer, question["expected_answer"]),
                         "retrieval_hit": hit_at_k(chunks, gold_chunks, args.top_k),
                         "concept_recall": concept_recall(concepts, gold_concepts),
                         "prerequisite_recall": prerequisite_recall(list(dict.fromkeys(concepts + prereqs)), gold_prereqs),
                         "latency_ms": round(response.total_latency_ms, 2),
                         "generation_latency_ms": round(response.generation_latency_ms, 2),
                         "retrieval_latency_ms": round(result.latency_ms, 2)})
            print(f"{architecture} {question['question_id']} provider={used_provider} latency={response.total_latency_ms:.0f}ms")
    output = project_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    summary = {"experiment": metadata, "architectures": {}}
    for name in selected:
        group = [r for r in rows if r["architecture"] == name]
        ok = [r for r in group if r["status"] == "ok"]
        summary["architectures"][name] = {
            "requests": len(group), "successful": len(ok), "failed": len(group) - len(ok),
            "fallbacks": sum(bool(r.get("fallback_used")) for r in ok),
            "providers": sorted({r.get("provider") for r in ok}),
            "mean_latency_ms": round(statistics.mean([r["latency_ms"] for r in ok]), 2) if ok else None,
            "mean_generation_latency_ms": round(statistics.mean([r["generation_latency_ms"] for r in ok]), 2) if ok else None,
            "mean_token_f1": round(statistics.mean([r["token_f1"] for r in ok]), 4) if ok else None,
            "retrieval_hit": round(statistics.mean([r["retrieval_hit"] for r in ok]), 4) if ok else None,
            "concept_recall": round(statistics.mean([r["concept_recall"] for r in ok]), 4) if ok else None,
            "prerequisite_recall": round(statistics.mean([r["prerequisite_recall"] for r in ok]), 4) if ok else None,
        }
    summary_path = output.with_name(output.stem + "_summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "summary": str(summary_path), "rows": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--architectures", nargs="+", choices=sorted(ARCHITECTURES))
    parser.add_argument("--dataset")
    parser.add_argument("--split", default="validation")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", default="data/evaluation/llm_architectures_pep_v3.jsonl")
    run(parser.parse_args())
