#!/usr/bin/env python3
from __future__ import annotations

import argparse,json
from datetime import datetime,timezone

from ai_tutor.experiments.batch import write_csv
from ai_tutor.experiments.profile_experiment import (
    METHODS,PROFILES,counterfactual_summary,evaluate_profile_case,
    simulated_profiles,summarize_profile_rows,
)
from ai_tutor.retrieval.factory import load_retriever
from ai_tutor.utils.io import read_jsonl,write_jsonl
from ai_tutor.utils.paths import load_config,project_path


def main():
    parser=argparse.ArgumentParser(description="Experimento contrafactual con perfiles simulados")
    parser.add_argument("--split",default="validation",choices=["train","validation"])
    parser.add_argument("--limit",type=int,default=30)
    parser.add_argument("--top-k",type=int,default=5)
    parser.add_argument("--run-id")
    args=parser.parse_args()
    cfg=load_config()
    questions=[q for q in read_jsonl(project_path(cfg["paths"]["questions"]))
               if q.get("split")==args.split and q.get("gold_prerequisite_ids")]
    questions=questions[:args.limit]
    retrievers={method:load_retriever(method) for method in METHODS}
    rows=[]
    for question in questions:
        profiles=simulated_profiles(question)
        for method,retriever in retrievers.items():
            for profile_name in PROFILES:
                rows.append(evaluate_profile_case(
                    question,method,profile_name,profiles[profile_name],retriever,args.top_k))
    run_id=args.run_id or datetime.now().strftime("profiles-%Y%m%d-%H%M%S")
    run_dir=project_path("data/evaluation/runs")/run_id
    run_dir.mkdir(parents=True,exist_ok=True)
    summary=summarize_profile_rows(rows)
    counterfactual=counterfactual_summary(rows)
    report={"run_id":run_id,"created_at":datetime.now(timezone.utc).isoformat(),
            "design":"within-question counterfactual learner profiles",
            "split":args.split,"questions":len(questions),"top_k":args.top_k,
            "methods":list(METHODS),"profiles":list(PROFILES),
            "profile_summary":summary,"counterfactual_summary":counterfactual,
            "interpretation":{
                "chunk_jaccard_distance":"0=invariante; valores mayores indican adaptación del contexto al perfil",
                "prerequisite_recall_lift":"recall con brecha menos recall con dominio alto; positivo favorece adaptación",
                "prerequisite_context_lift":"proporción de chunks de prerrequisito con brecha menos dominio alto",
                "target_recall_cost":"pérdida de recall del concepto objetivo al adaptar; cerca de 0 es deseable",
            }}
    write_jsonl(run_dir/"profile_results.jsonl",rows)
    write_csv(run_dir/"profile_results.csv",rows)
    write_csv(run_dir/"profile_summary.csv",summary)
    write_csv(run_dir/"counterfactual_summary.csv",counterfactual)
    (run_dir/"summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
