from ai_tutor.graph.spreading_activation import spread_activation
import networkx as nx

def test_activation_reaches_prerequisites_and_stops(graph):
    result=spread_activation(graph,{"quadratic":1.0},{"max_iterations":20,"early_stopping_tolerance":1e-3,"activation_threshold":0,"activation_decay":.05,"retention":.3,"propagation_rate":.6,"prerequisite_weight":1.2,"top_population":10})
    assert result.final.get("factorization",0)>0
    assert result.iterations<=20

def test_activation_respects_population_bounds():
    graph=nx.DiGraph()
    for i in range(100):graph.add_node(f"c{i}",node_type="Concept")
    for i in range(99):graph.add_edge(f"c{i}",f"c{i+1}",edge_type="PREREQUISITE_OF",weight=1)
    result=spread_activation(graph,{"c99":1.0},{"max_hops":2,"max_nodes":10,"max_neighbors_per_node":2,"max_iterations":3})
    assert result.nodes_visited<=10
    assert result.nodes_visited<100

def test_query_restart_preserves_seed_signal():
    graph=nx.DiGraph(); graph.add_node("seed",node_type="Concept")
    result=spread_activation(graph,{"seed":1.0},{"retention":0.0,"propagation_rate":0.0,"activation_decay":0.0,"query_restart":0.2,"max_iterations":3,"activation_threshold":0})
    assert result.final["seed"]>0
