from __future__ import annotations
from collections import deque


def build_learning_path(graph, targets, student_state, concept_labels, max_depth=3, max_nodes=24, mastery_threshold=0.65):
    """Trace a bounded prerequisite DAG backwards from the detected targets."""
    distances = {target: 0 for target in targets if target in graph}
    parent = {}
    queue = deque(sorted(distances))
    edges = []
    while queue and len(distances) < max_nodes:
        node = queue.popleft()
        if distances[node] >= max_depth:
            continue
        prereqs = sorted(source for source, _, data in graph.in_edges(node, data=True)
                         if data.get("edge_type") == "PREREQUISITE_OF")
        for prerequisite in prereqs:
            edges.append((prerequisite, node))
            if prerequisite not in distances:
                distances[prerequisite] = distances[node] + 1
                parent[prerequisite] = node
                queue.append(prerequisite)
                if len(distances) >= max_nodes:
                    break
    mastery = {node: student_state.mastery_for(node, concept_labels.get(node, "")) for node in distances}
    missing = [node for node in distances if node not in targets and mastery[node] < mastery_threshold]
    missing.sort(key=lambda node: (-distances[node], mastery[node], node))
    ordered = missing + [target for target in targets if target in distances]
    return {
        "target_concepts": list(targets), "ordered_concepts": ordered,
        "missing_prerequisites": missing, "distances": distances,
        "mastery": mastery, "edges": edges, "mastery_threshold": mastery_threshold,
    }
