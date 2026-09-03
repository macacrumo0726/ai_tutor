#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,cProfile,pstats,io
from ai_tutor.retrieval.factory import load_retriever

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--method",default="pep_sa_rag",choices=["rag","graph_rag","pep_sa_rag","pep_plan_rag"]); parser.add_argument("--query",default="¿Cómo encuentro las raíces de x² - 5x + 6?"); parser.add_argument("--top-k",type=int,default=5); args=parser.parse_args()
    profiler=cProfile.Profile(); retriever=load_retriever(args.method); profiler.enable(); result=retriever.retrieve(args.query,args.top_k); profiler.disable()
    stream=io.StringIO(); pstats.Stats(profiler,stream=stream).sort_stats("cumulative").print_stats(20)
    fields={"total_latency":result.latency_ms,"retrieval_latency":result.debug_info.get("retrieval_latency_ms",result.latency_ms),"graph_latency":result.debug_info.get("graph_latency_ms",0),"population_dynamics_latency":result.debug_info.get("population_dynamics_latency_ms",0),"reranking_latency":result.debug_info.get("reranking_latency_ms",0),"generation_latency":0,"nodes_visited":result.debug_info.get("nodes_visited",0),"edges_visited":result.debug_info.get("edges_visited",0),"iterations":result.debug_info.get("iterations",0)}
    print(json.dumps(fields,ensure_ascii=False,indent=2)); print(stream.getvalue())
if __name__=="__main__": main()
