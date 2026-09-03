from __future__ import annotations
import networkx as nx
from ai_tutor.instructional.prerequisites import prerequisite_edges

def build_pedagogical_graph(concepts,chunks,units=None,questions=None,relations=None):
    # MultiDiGraph preserves distinct pedagogical relations between the same
    # concepts (e.g. NEXT_CONCEPT and PREREQUISITE_OF).
    graph=nx.MultiDiGraph()
    for c in concepts: graph.add_node(c["concept_id"],node_type="Concept",**c)
    if relations:
        for relation in relations:
            if relation["source_id"] in graph and relation["target_id"] in graph:
                graph.add_edge(relation["source_id"],relation["target_id"],edge_type=relation["edge_type"],weight=relation["weight"],source=relation["source"],confidence=relation["confidence"])
    else:
        for pre,target,attrs in prerequisite_edges(concepts):
            if pre in graph and target in graph: graph.add_edge(pre,target,**attrs)
    for c in chunks:
        node=f"chunk::{c['chunk_id']}"; graph.add_node(node,node_type="Chunk",**c)
        for cid in c.get("concept_ids",[]):
            if cid in graph: graph.add_edge(node,cid,edge_type="MENTIONS",weight=1.0,source="corpus",confidence=1.0); graph.add_edge(cid,node,edge_type="EXPLAINS",weight=1.0,source="corpus",confidence=1.0)
    for u in units or []:
        node=f"unit::{u['instructional_unit_id']}"; graph.add_node(node,node_type="InstructionalUnit",**u); graph.add_edge(node,u["concept_id"],edge_type="EXPLAINS",weight=1.0,source="dataset",confidence=1.0)
    for q in questions or []:
        node=f"question::{q['question_id']}"; graph.add_node(node,node_type="Question",**q)
        for cid in q["required_concepts"]: graph.add_edge(node,cid,edge_type="REQUIRES",weight=1.0,source=q["source"],confidence=1.0)
    return graph
