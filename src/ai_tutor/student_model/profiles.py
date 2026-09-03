from __future__ import annotations
from copy import deepcopy
from .schema import StudentState


STUDENT_PROFILES = {
    "unknown": StudentState(profile_id="unknown", default_mastery=0.50, confidence=0.0),
    "high_mastery": StudentState(profile_id="high_mastery", default_mastery=0.85, confidence=0.75),
    "algebra_gap": StudentState(
        profile_id="algebra_gap", default_mastery=0.65,
        gap_keywords=["algebra", "factor", "ecuacion", "exponente", "radical", "fraccion"], confidence=0.70,
    ),
    "prerequisite_gap": StudentState(
        profile_id="prerequisite_gap", default_mastery=0.60,
        gap_keywords=["prerequis", "fundamento", "numero", "operacion", "propiedad"], confidence=0.65,
    ),
    "misconception": StudentState(
        profile_id="misconception", default_mastery=0.55,
        misconceptions=["aplica una regla sin comprobar sus condiciones", "confunde definición y procedimiento"], confidence=0.65,
    ),
}


def get_student_profile(profile="unknown") -> StudentState:
    if isinstance(profile, StudentState):
        return profile
    if profile not in STUDENT_PROFILES:
        raise ValueError(f"Unknown student profile: {profile}")
    return deepcopy(STUDENT_PROFILES[profile])
