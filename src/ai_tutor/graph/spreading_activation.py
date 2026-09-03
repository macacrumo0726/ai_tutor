from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import networkx as nx

@dataclass
class ActivationResult:
    final:dict[str,float]; history:list[dict[str,float]]; iterations:int; nodes_visited:int; edges_visited:int

def spread_activation(graph:nx.DiGraph,seeds:dict[str,float],config:dict)->ActivationResult:
    # Build a bounded concept neighborhood, prioritizing incoming prerequisite
    # edges so activation can flow from a target concept to prior knowledge.
    max_nodes=config.get("max_nodes",80); max_hops=config.get("max_hops",2)
    neighbor_limit=config.get("max_neighbors_per_node",12)
    active={n for n in seeds if n in graph and graph.nodes[n].get("node_type")=="Concept"}
    frontier=sorted(active)
    for _ in range(max_hops):
        nxt=[]
        for node in frontier:
            incoming=[s for s,_,d in graph.in_edges(node,data=True) if d.get("edge_type")=="PREREQUISITE_OF"]
            adjacent=list(graph.predecessors(node))+list(graph.successors(node))
            candidates=list(dict.fromkeys(incoming+adjacent))
            candidates=[n for n in candidates if n in graph and graph.nodes[n].get("node_type")=="Concept"]
            for candidate in candidates[:neighbor_limit]:
                if candidate not in active:
                    active.add(candidate); nxt.append(candidate)
                    if len(active)>=max_nodes:break
            if len(active)>=max_nodes:break
        frontier=nxt
        if not frontier or len(active)>=max_nodes:break
    nodes=sorted(active)
    index={n:i for i,n in enumerate(nodes)}; n=len(nodes); matrix=np.zeros((n,n),dtype=np.float32); edges=0
    type_weight={"PREREQUISITE_OF":config.get("prerequisite_weight",1.25),"RELATED_TO":config.get("related_weight",.45)}
    forward_weight=config.get("forward_successor_weight",0.0)
    for source,target,data in graph.edges(nodes,data=True):
        if source not in index or target not in index: continue
        w=float(data.get("weight",1))*type_weight.get(data.get("edge_type"),.25)
        # Reverse prerequisite flow supports required prior knowledge.
        if data.get("edge_type")=="PREREQUISITE_OF":
            matrix[index[source],index[target]]+=w
            if forward_weight:matrix[index[target],index[source]]+=float(data.get("weight",1))*forward_weight
        else: matrix[index[target],index[source]]+=w
        edges+=1
    cols=matrix.sum(axis=0); cols[cols==0]=1; matrix/=cols
    seed_vector=np.array([seeds.get(node,0.0) for node in nodes],dtype=np.float32)
    a=seed_vector.copy(); history=[dict(zip(nodes,map(float,a)))]
    retention=config.get("retention",.35); rate=config.get("propagation_rate",.65); restart=config.get("query_restart",0.0)
    decay=config.get("activation_decay",.02); threshold=config.get("activation_threshold",.001); tol=config.get("early_stopping_tolerance",1e-4)
    stable_required=config.get("ranking_stability_patience",0); stable_count=0; previous_top=None
    for iteration in range(1,config.get("max_iterations",12)+1):
        incoming=np.einsum("ij,j->i",matrix,a,optimize=False)
        new=np.maximum(0,retention*a+rate*incoming+restart*seed_vector-decay*a); new[new<threshold]=0
        history.append(dict(zip(nodes,map(float,new))))
        current_top=tuple(nodes[i] for i in np.argsort(-new)[:config.get("top_population",20)] if new[i]>0)
        stable_count=stable_count+1 if current_top==previous_top else 0; previous_top=current_top
        if float(np.max(np.abs(new-a)))<tol or (stable_required and stable_count>=stable_required): a=new; break
        a=new
    final=sorted(zip(nodes,map(float,a)),key=lambda x:-x[1])[:config.get("top_population",20)]
    return ActivationResult(dict(final),history,iteration,n,edges)
