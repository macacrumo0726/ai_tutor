"""Small dependency-free personalized PageRank implementation.

NetworkX delegates ``nx.pagerank`` to SciPy when SciPy is installed, but that
creates an accidental dependency for the minimal API/CI environment.  The
explicit power iteration below is transparent, deterministic, and sufficient
for the bounded pedagogical subgraphs used by the retrievers.
"""


def personalized_pagerank(graph, seeds, alpha=.85, max_iter=100, tol=1e-6):
    if not seeds or not graph:
        return {}
    nodes = list(graph)
    valid = [seed for seed in seeds if seed in graph]
    if not valid:
        return {}

    personalization = {node: 0.0 for node in nodes}
    for seed in valid:
        personalization[seed] += 1.0 / len(valid)
    rank = dict(personalization)

    outgoing = {}
    for node in nodes:
        weighted_edges = []
        total_weight = 0.0
        for _, target, data in graph.out_edges(node, data=True):
            weight = float(data.get("weight", 1.0))
            if weight > 0:
                weighted_edges.append((target, weight))
                total_weight += weight
        outgoing[node] = (weighted_edges, total_weight)

    for _ in range(max_iter):
        next_rank = {
            node: (1.0 - alpha) * personalization[node]
            for node in nodes
        }
        dangling_mass = sum(
            rank[node] for node, (_, total_weight) in outgoing.items()
            if total_weight <= 0
        )
        for node in nodes:
            next_rank[node] += alpha * dangling_mass * personalization[node]
        for node, (edges, total_weight) in outgoing.items():
            if total_weight <= 0:
                continue
            share = alpha * rank[node] / total_weight
            for target, weight in edges:
                next_rank[target] += share * weight
        delta = sum(abs(next_rank[node] - rank[node]) for node in nodes)
        rank = next_rank
        if delta <= len(nodes) * tol:
            break
    return rank
