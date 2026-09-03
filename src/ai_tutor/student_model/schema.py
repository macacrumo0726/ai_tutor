from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class StudentState:
    """Minimal, inspectable learner model used by PEP-Plan-RAG v3."""

    profile_id: str = "unknown"
    default_mastery: float = 0.50
    concept_mastery: dict[str, float] = field(default_factory=dict)
    gap_keywords: list[str] = field(default_factory=list)
    misconceptions: list[str] = field(default_factory=list)
    confidence: float = 0.50
    evidence_count: int = 0

    def mastery_for(self, concept_id: str, concept_name: str = "") -> float:
        if concept_id in self.concept_mastery:
            return min(1.0, max(0.0, float(self.concept_mastery[concept_id])))
        searchable = f"{concept_id} {concept_name}".lower()
        if any(keyword.lower() in searchable for keyword in self.gap_keywords):
            return 0.20
        return min(1.0, max(0.0, float(self.default_mastery)))

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "default_mastery": self.default_mastery,
            "concept_mastery": dict(self.concept_mastery),
            "gap_keywords": list(self.gap_keywords),
            "misconceptions": list(self.misconceptions),
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
        }
