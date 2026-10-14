from __future__ import annotations
from dataclasses import asdict, dataclass, field


@dataclass
class MicroCheck:
    micro_check_id: str
    concept_id: str
    question: str
    expected_answer: str
    answer_type: str
    validator: str
    hint_sequence: list[str] = field(default_factory=list)
    difficulty: str = "basic"
    tolerance: float = 1e-6
    source: str = "curated_research_bank"

    def to_dict(self): return asdict(self)


@dataclass
class AssessmentResult:
    correct: bool
    score: float
    normalized_answer: str
    feedback: str
    validator: str

    def to_dict(self): return asdict(self)


@dataclass
class PedagogicalDecision:
    action: str
    reason: str
    hint_level: int = 0
    next_concept_id: str = ""

    def to_dict(self): return asdict(self)
