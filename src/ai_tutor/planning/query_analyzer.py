from __future__ import annotations


def analyze_query(query: str, target_concepts: list[str], instructional_units: dict) -> dict:
    text = query.lower()
    if any(word in text for word in ("por qué", "que significa", "qué significa", "define", "concepto")):
        query_type = "conceptual"
    elif any(word in text for word in ("error", "incorrect", "confund", "siempre", "nunca")):
        query_type = "misconception"
    elif any(word in text for word in ("aplica", "situación", "problema", "modelo")):
        query_type = "application"
    else:
        query_type = "procedural"
    detected = []
    for concept_id in target_concepts:
        unit = instructional_units.get(concept_id, {})
        for misconception in unit.get("common_misconceptions", []):
            terms = [term.strip(".,:;¿?") for term in misconception.lower().split() if len(term) > 5]
            if terms and sum(term in text for term in terms) >= min(2, len(terms)):
                detected.append({"concept_id": concept_id, "text": misconception})
    return {"query_type": query_type, "target_concepts": target_concepts, "detected_misconceptions": detected}
