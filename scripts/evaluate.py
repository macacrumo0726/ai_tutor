#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from ai_tutor.evaluation.evaluator import evaluate_one,git_commit
from ai_tutor.tutoring.tutor import Tutor
from ai_tutor.utils.io import read_jsonl,write_jsonl
from ai_tutor.utils.paths import load_config,project_path

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--methods",nargs="+",default=["rag","graph_rag","pep_sa_rag","pep_plan_rag"]); parser.add_argument("--dataset"); parser.add_argument("--split",default="test"); parser.add_argument("--limit",type=int); parser.add_argument("--output",default="data/evaluation/results.jsonl"); parser.add_argument("--top-k",type=int,default=5); args=parser.parse_args()
    cfg=load_config(); path=project_path(args.dataset or cfg["paths"]["questions"]); questions=[q for q in read_jsonl(path) if args.split=="all" or q.get("split")==args.split]
    if args.limit: questions=questions[:args.limit]
    metadata={"git_commit":git_commit(),"config":cfg,"model":cfg["generation"]["model"],"embedding_model":cfg["embedding"]["model"],"dataset_version":cfg["project"]["dataset_version"],"seed":cfg["project"]["seed"]}
    tutor=Tutor(); rows=[]
    for question in questions:
        for method in args.methods:
            row=evaluate_one(tutor,question,method,args.top_k,metadata); rows.append(row); print(f"{question['question_id']} {method} {row['latency_ms']:.2f}ms")
    write_jsonl(project_path(args.output),rows); print(f"saved={len(rows)} path={project_path(args.output)}")
if __name__=="__main__": main()
