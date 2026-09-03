#!/usr/bin/env python3
"""Build a provenance-aware conversational dataset for pedagogical SFT."""
from __future__ import annotations
import argparse,json
from ai_tutor.utils.io import read_jsonl,write_jsonl
from ai_tutor.utils.paths import load_config,project_path

SYSTEM="Eres un tutor de Precálculo. Diagnostica, activa conocimientos previos, guía con scaffolding y usa micro-checks. No inventes fuentes."

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",default="data/training/precalculus_sft.jsonl"); args=parser.parse_args()
    cfg=load_config(); units={u["concept_id"]:u for u in read_jsonl(project_path(cfg["paths"]["instructional_units"]))}; questions=read_jsonl(project_path(cfg["paths"]["questions"])); rows=[]
    for question in questions:
        unit=units[question["concept_id"]]
        # Only corpus-grounded content becomes target knowledge; generated fields
        # remain metadata and are excluded from supervised targets by default.
        explanation=unit["concept_explanation"]
        if not explanation or unit["provenance"].get("concept_explanation")!="corpus": continue
        prereqs=", ".join(unit["prerequisite_concepts"]) or "ninguno explícito"
        answer=(f"Primero identifiquemos la dificultad. Para este tema conviene recordar: {prereqs}.\n\n"
                f"Idea clave: {explanation[:700]}\n\n"
                f"Ahora intenta este micro-check: {unit['diagnostic_question']}")
        rows.append({"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":question["question"]},{"role":"assistant","content":answer}],"concept_id":question["concept_id"],"split":question["split"],"provenance":"corpus_grounded_template","dataset_version":cfg["project"]["dataset_version"]})
    write_jsonl(project_path(args.output),rows); print(f"examples={len(rows)} path={project_path(args.output)}")
if __name__=="__main__": main()

