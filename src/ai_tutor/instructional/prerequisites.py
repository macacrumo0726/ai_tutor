def prerequisite_edges(concepts: list[dict]) -> list[tuple[str, str, dict]]:
    return [(pre, c["concept_id"], {"edge_type":"PREREQUISITE_OF", "weight":1.0,
            "source":"expert_curated_seed", "confidence":0.8}) for c in concepts for pre in c["prerequisites"]]
