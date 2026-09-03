#!/usr/bin/env python3
from __future__ import annotations
import pickle
from ai_tutor.graph.builder import build_pedagogical_graph
from ai_tutor.utils.io import read_jsonl
from ai_tutor.utils.paths import load_config,project_path

def main():
    cfg=load_config(); paths=cfg["paths"]
    values={key:read_jsonl(project_path(paths[key])) for key in ("chunks","concepts","instructional_units","questions","relations")}
    graph=build_pedagogical_graph(values["concepts"],values["chunks"],values["instructional_units"],values["questions"],values["relations"])
    path=project_path(paths["graph"]); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("wb") as handle: pickle.dump(graph,handle)
    print(f"nodes={graph.number_of_nodes()} edges={graph.number_of_edges()} path={path}")
if __name__=="__main__": main()
