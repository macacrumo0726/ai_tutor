#!/usr/bin/env python3
from __future__ import annotations
import argparse
from ai_tutor.evaluation.evaluator import evaluate_condition,git_commit
from ai_tutor.tutoring.tutor import Tutor
from ai_tutor.utils.io import read_jsonl,write_jsonl
from ai_tutor.utils.paths import load_config,project_path

CONDITIONS=("raw","pedagogical_prompt","rag","graph_rag","pep_sa_rag")

def main():
    parser=argparse.ArgumentParser(description="Evaluación controlada Gemini-first")
    parser.add_argument("--conditions",nargs="+",choices=CONDITIONS,default=list(CONDITIONS))
    parser.add_argument("--dataset"); parser.add_argument("--split",default="test")
    parser.add_argument("--limit",type=int); parser.add_argument("--top-k",type=int,default=5)
    parser.add_argument("--output",default="data/evaluation/gemini_pilot_results.jsonl")
    args=parser.parse_args(); cfg=load_config()
    questions=[q for q in read_jsonl(project_path(args.dataset or cfg["paths"]["questions"])) if args.split=="all" or q.get("split")==args.split]
    if args.limit: questions=questions[:args.limit]
    metadata={"experiment_id":"gemini-pilot-v1","git_commit":git_commit(),"model_family":"gemini",
        "adaptation":"original","model":cfg["generation"]["default_models"]["gemini"],
        "embedding_model":cfg["embedding"]["model"],"dataset_version":cfg["project"]["dataset_version"],"seed":cfg["project"]["seed"]}
    tutor=Tutor(generator_provider="gemini"); rows=[]
    for question in questions:
        for condition in args.conditions:
            row=evaluate_condition(tutor,question,condition,args.top_k,metadata); rows.append(row)
            print(f"{question['question_id']} {condition} {row['latency_ms']:.2f}ms")
    output=project_path(args.output); write_jsonl(output,rows); print(f"saved={len(rows)} path={output}")

if __name__=="__main__": main()
