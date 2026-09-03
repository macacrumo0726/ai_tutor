from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

PROVENANCE = {"corpus", "generated", "inferred", "expert_curated"}

@dataclass
class Concept:
    concept_id: str
    concept_name: str
    canonical_name: str
    description: str
    topic: str
    subtopic: str
    difficulty: str
    learning_objective: str
    prerequisites: list[str] = field(default_factory=list)
    successors: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    source_pages: list[int] = field(default_factory=list)
    source_chunks: list[str] = field(default_factory=list)
    provenance: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.concept_id or not self.canonical_name:
            raise ValueError("A concept needs concept_id and canonical_name")
        invalid = set(self.provenance.values()) - PROVENANCE
        if invalid:
            raise ValueError(f"Invalid provenance values: {invalid}")

    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass
class InstructionalUnit:
    instructional_unit_id: str
    concept_id: str
    learning_objective: str
    prerequisite_concepts: list[str]
    concept_explanation: str
    worked_example: str
    guided_example: str
    common_misconceptions: list[str]
    diagnostic_question: str
    practice_question: str
    hint_level_1: str
    hint_level_2: str
    hint_level_3: str
    solution: str
    difficulty: str
    source_reference: dict[str, Any]
    provenance: dict[str, str]

    def validate(self) -> None:
        if not self.instructional_unit_id or not self.concept_id:
            raise ValueError("Instructional unit identifiers are required")
        invalid = set(self.provenance.values()) - PROVENANCE
        if invalid: raise ValueError(f"Invalid provenance values: {invalid}")
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass
class Chunk:
    chunk_id: str
    text: str
    page_start: int
    page_end: int
    section: str
    topic: str
    subtopic: str
    concept_ids: list[str]
    difficulty: str
    chunk_type: str
    source: str
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass
class Question:
    question_id: str
    question: str
    expected_answer: str
    concept_id: str
    required_concepts: list[str]
    required_prerequisites: list[str]
    difficulty: str
    question_type: str
    source: str
    split: str
    gold_chunk_ids: list[str] = field(default_factory=list)
    gold_concept_ids: list[str] = field(default_factory=list)
    gold_prerequisite_ids: list[str] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]: return asdict(self)

