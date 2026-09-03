def retrieval_table(result):
    return [{"chunk_id":c.chunk_id,"score":c.score,"concept_ids":c.concept_ids,"preview":c.text[:160]} for c in result.chunks]

