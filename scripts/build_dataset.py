#!/usr/bin/env python3
from __future__ import annotations
import argparse
import pandas as pd
import fitz
from ai_tutor.instructional.comprehensive_builder import build_database
from ai_tutor.utils.io import write_jsonl
from ai_tutor.utils.paths import load_config,project_path

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--limit",type=int); args=parser.parse_args()
    cfg=load_config(); source=project_path(cfg["paths"]["legacy_chunks"])
    if not source.exists(): raise SystemExit(f"Missing legacy chunks: {source}")
    df=pd.read_parquet(source); rows=df.head(args.limit).to_dict("records") if args.limit else df.to_dict("records")
    pdf_path=project_path("doctorado/libro/libro.pdf")
    with fitz.open(pdf_path) as doc:
        toc=doc.get_toc(); page_texts=[page.get_text() for page in doc]
    chunks,concepts,units,questions,relations=build_database(toc,page_texts,rows)
    for key,data in [("chunks",chunks),("concepts",concepts),("instructional_units",units),("questions",questions),("relations",relations)]: write_jsonl(project_path(cfg["paths"][key]),data)
    print(f"chunks={len(chunks)} concepts={len(concepts)} units={len(units)} questions={len(questions)} relations={len(relations)}")
if __name__=="__main__": main()
