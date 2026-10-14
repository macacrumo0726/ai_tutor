from __future__ import annotations
import re
import unicodedata

from ai_tutor.student_model import StudentState


FEEDBACK_OUTCOMES = {
    "understood": 1.0,
    "partial": 0.6,
    "needs_help": 0.2,
    "incorrect": 0.0,
}


class LearningProfileService:
    """Turns explicit learning evidence into an inspectable longitudinal state."""

    def __init__(self, repository):
        self.repository = repository

    def state_for(self, user_id: str) -> StudentState:
        profile = self.repository.get_student_profile(user_id)
        mastery_rows = self.repository.get_mastery(user_id)
        misconceptions = self.repository.learning_report(user_id)["misconceptions"]
        return StudentState(
            profile_id=f"persistent:{self.repository.normalize_user_id(user_id)}",
            default_mastery=float(profile["default_mastery"]),
            concept_mastery={row["concept_id"]: float(row["mastery"]) for row in mastery_rows},
            misconceptions=[row["misconception"] for row in misconceptions if row["status"] != "resolved"],
            confidence=float(profile["confidence"]),
            evidence_count=int(profile["evidence_count"]),
        )

    def record_feedback(self, user_id: str, concept_ids: list[str], feedback: str,
                        conversation_id=None, metadata=None):
        if feedback not in FEEDBACK_OUTCOMES:
            raise ValueError(f"Unknown feedback: {feedback}")
        unique = list(dict.fromkeys(concept_ids or []))
        if not unique:
            raise ValueError("No hay conceptos recuperados para asociar la evidencia")
        updates = [self.repository.add_learning_evidence(
            user_id, concept_id, "explicit_feedback", FEEDBACK_OUTCOMES[feedback],
            "student_self_report", conversation_id, metadata,
        ) for concept_id in unique]
        self.repository.add_learning_event(user_id, "profile_updated", {
            "feedback": feedback, "concept_ids": unique, "updates": updates,
        }, conversation_id)
        return {"feedback": feedback, "outcome": FEEDBACK_OUTCOMES[feedback],
                "updates": updates, "student_state": self.state_for(user_id).to_dict()}

    @staticmethod
    def _normalized(text):
        value=unicodedata.normalize("NFKD",text.lower())
        return " ".join("".join(ch for ch in value if not unicodedata.combining(ch)).split())

    def infer_from_response(self, user_id: str, message: str, prior_messages,
                            conversation_id=None, fallback_concepts=None):
        """Extract low-weight evidence from a student's conversational reply.

        Linguistic self-reports may adjust mastery conservatively. A short answer
        to a tutor question is stored as unscored evidence but cannot change
        mastery until correctness can be verified.
        """
        previous_assistant=next((item for item in reversed(prior_messages or []) if item.role=="assistant"),None)
        if previous_assistant is None:
            return None
        concepts=list(dict.fromkeys(previous_assistant.metadata.get("concepts",[]) or fallback_concepts or []))
        if not concepts:
            return None
        normalized=self._normalized(message)
        patterns=(
            ("confusion_report",0.15,(r"\bno entiendo\b",r"\bno entendi\b",r"\bestoy perdid",r"\bme confundi",r"\bno se como\b")),
            ("partial_understanding",0.55,(r"\bmas o menos\b",r"\bentiendo una parte\b",r"\bcreo que\b",r"\bno estoy segur")),
            ("understanding_report",0.90,(r"\bya entendi\b",r"\bahora entiendo\b",r"\bme quedo claro\b",r"\btiene sentido\b",r"\blo comprendi\b")),
            ("help_request",0.25,(r"\bexplica otra vez\b",r"\bnecesito ayuda\b",r"\bno me queda claro\b")),
        )
        signal=None
        for evidence_type,outcome,expressions in patterns:
            if any(re.search(expression,normalized) for expression in expressions):
                signal=(evidence_type,outcome,0.25)
                break
        if signal is None:
            asks_micro_check="?" in previous_assistant.content
            if not asks_micro_check or len(message.strip())>160:
                return None
            signal=("unscored_student_response",0.50,0.0)
        evidence_type,outcome,weight=signal
        updates=[self.repository.add_learning_evidence(
            user_id,concept_id,evidence_type,outcome,"conversation_inference",conversation_id,
            {"student_message":message[:500],"extractor":"deterministic_rules_v1"},weight,
        ) for concept_id in concepts[:5]]
        result={"evidence_type":evidence_type,"outcome":outcome,"weight":weight,
                "concept_ids":concepts[:5],"updates":updates,
                "changes_mastery":weight>0}
        self.repository.add_learning_event(user_id,"implicit_evidence_extracted",result,conversation_id)
        return result
