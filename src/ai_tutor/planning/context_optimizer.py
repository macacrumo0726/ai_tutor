from __future__ import annotations
import re


def _tokens(text):
    return set(re.findall(r"[a-záéíóúñ0-9]+", text.lower()))


def _redundancy(candidate, selected):
    tokens = _tokens(candidate.text)
    values = []
    for other in selected:
        other_tokens = _tokens(other.text)
        union = tokens | other_tokens
        values.append(len(tokens & other_tokens) / len(union) if union else 0.0)
    return max(values, default=0.0)


def optimize_context(ranked, top_k, direct_ids, prerequisite_ids, utility, redundancy_weight=0.12,
                     min_direct=2, min_prerequisite=1, min_instructional=1):
    selected = []
    buckets = {}
    instructional = {"definition", "explanation", "worked_example", "example"}

    def take(label, predicate, count):
        choices = [chunk for chunk in ranked if predicate(chunk) and chunk not in selected]
        while choices and sum(value == label for value in buckets.values()) < count and len(selected) < top_k:
            best = max(choices, key=lambda chunk: utility[chunk.chunk_id] - redundancy_weight * _redundancy(chunk, selected))
            selected.append(best); buckets[best.chunk_id] = label; choices.remove(best)

    take("direct", lambda chunk: chunk.chunk_id in direct_ids, min(min_direct, top_k))
    take("prerequisite", lambda chunk: any(cid in prerequisite_ids for cid in chunk.concept_ids),
         min(min_prerequisite, max(0, top_k - len(selected))))
    take("instructional", lambda chunk: chunk.metadata.get("chunk_type") in instructional,
         min(min_instructional, max(0, top_k - len(selected))))
    while len(selected) < top_k:
        remaining = [chunk for chunk in ranked if chunk not in selected]
        if not remaining:
            break
        best = max(remaining, key=lambda chunk: utility[chunk.chunk_id] - redundancy_weight * _redundancy(chunk, selected))
        selected.append(best); buckets[best.chunk_id] = "utility"
    return selected, buckets
