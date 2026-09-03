import networkx as nx

def personalized_pagerank(graph,seeds,alpha=.85):
    if not seeds: return {}
    personalization={n:0.0 for n in graph}; valid=[s for s in seeds if s in graph]
    if not valid: return {}
    for seed in valid: personalization[seed]=1/len(valid)
    return nx.pagerank(graph,alpha=alpha,personalization=personalization,weight="weight")

