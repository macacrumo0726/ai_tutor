#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,time
from datetime import datetime
from pathlib import Path

from ai_tutor.evaluation.evaluator import evaluate_condition,git_commit
from ai_tutor.experiments.batch import run_retrieval,run_ablations,run_robustness,summarize,summarize_generation,write_blinded_rubric,write_csv,manifest
from ai_tutor.experiments.report import update_presentation
from ai_tutor.tutoring.tutor import Tutor
from ai_tutor.utils.io import read_jsonl,write_jsonl
from ai_tutor.utils.paths import load_config,project_path

def save_stage(run_dir:Path,name:str,rows:list[dict],group_key="method"):
    write_jsonl(run_dir/f"{name}.jsonl",rows); write_csv(run_dir/f"{name}.csv",rows)
    valid=[r for r in rows if group_key in r]
    summary=summarize(valid,group_key) if valid else []
    (run_dir/f"{name}_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    return summary

def main():
    parser=argparse.ArgumentParser(description="Pipeline masivo de experimentos del tutor")
    parser.add_argument("--stages",nargs="+",choices=["retrieval","ablations","robustness","generation","all"],default=["retrieval","ablations"])
    parser.add_argument("--split",default="validation",choices=["train","validation","test","all"])
    parser.add_argument("--limit",type=int); parser.add_argument("--top-k",type=int,default=5)
    parser.add_argument("--generation-conditions",nargs="+",default=["raw","pedagogical_prompt","rag","graph_rag","pep_sa_rag"])
    parser.add_argument("--generation-limit",type=int,default=30); parser.add_argument("--delay-seconds",type=float,default=1.0)
    parser.add_argument("--run-id"); parser.add_argument("--update-html",action="store_true")
    parser.add_argument("--confirm-test",action="store_true",help="Confirma una ejecución sobre el test retenido")
    args=parser.parse_args()
    if args.split=="test" and not args.confirm_test:raise SystemExit("El test está protegido. Añada --confirm-test solo con parámetros congelados.")
    stages=["retrieval","ablations","robustness","generation"] if "all" in args.stages else args.stages
    cfg=load_config(); questions=[q for q in read_jsonl(project_path(cfg["paths"]["questions"])) if args.split=="all" or q.get("split")==args.split]
    if args.limit:questions=questions[:args.limit]
    run_id=args.run_id or datetime.now().strftime("%Y%m%d-%H%M%S"); run_dir=project_path("data/evaluation/runs")/run_id; run_dir.mkdir(parents=True,exist_ok=True)
    meta=manifest({"run_id":run_id,"split":args.split,"question_count":len(questions),"top_k":args.top_k,"stages":stages,"git_commit":git_commit(),"seed":cfg["project"]["seed"],"dataset_version":cfg["project"]["dataset_version"],"model":cfg["generation"]["default_models"]["gemini"]})
    (run_dir/"manifest.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    summaries={}
    if "retrieval" in stages:
        rows=run_retrieval(questions,args.top_k); summaries["retrieval_summary"]=save_stage(run_dir,"retrieval",rows)
    if "ablations" in stages:
        rows=run_ablations(questions,args.top_k); summaries["ablation_summary"]=save_stage(run_dir,"ablations",rows)
    if "robustness" in stages:
        rows=run_robustness(questions,args.top_k); summaries["robustness_summary"]=save_stage(run_dir,"robustness",rows)
    if "generation" in stages:
        tutor=Tutor(generator_provider="gemini"); rows=[]
        generation_questions=questions[:args.generation_limit]
        metadata={**meta,"model_family":"gemini","adaptation":"original","embedding_model":cfg["embedding"]["model"]}
        for question in generation_questions:
            for condition in args.generation_conditions:
                try:row=evaluate_condition(tutor,question,condition,args.top_k,metadata)
                except Exception as exc:row={**metadata,"question_id":question["question_id"],"condition":condition,"error":str(exc)}
                rows.append(row); write_jsonl(run_dir/"generation.partial.jsonl",rows); time.sleep(args.delay_seconds)
        write_jsonl(run_dir/"generation.jsonl",rows); write_csv(run_dir/"generation.csv",rows)
        summaries["generation_summary"]=summarize_generation(rows,cfg["project"]["seed"])
        (run_dir/"generation_summary.json").write_text(json.dumps(summaries["generation_summary"],ensure_ascii=False,indent=2),encoding="utf-8")
        write_blinded_rubric(run_dir,rows,cfg["project"]["seed"])
    report={**meta,**summaries}; (run_dir/"summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    if args.update_html:update_presentation(project_path("docs/research-overview.html"),report)
    print(json.dumps({"run_id":run_id,"questions":len(questions),"run_dir":str(run_dir),"html_updated":args.update_html},ensure_ascii=False))

if __name__=="__main__":main()
