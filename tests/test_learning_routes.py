from ai_tutor.planning.learning_routes import build_learning_routes
from ai_tutor.student_model import StudentState


def test_learning_routes_group_concepts_and_expose_progress():
    concepts = [
        {"concept_id": "frac", "concept_name": "Fracciones algebraicas", "canonical_name": "fracciones"},
        {"concept_id": "exp", "concept_name": "Exponentes y radicales", "canonical_name": "exponentes"},
        {"concept_id": "dom", "concept_name": "Dominio de una función", "canonical_name": "dominio"},
    ]
    state = StudentState(profile_id="test", concept_mastery={"frac": .9, "exp": .4, "dom": .7})
    routes = build_learning_routes(concepts, state)
    fractions = next(item for item in routes if item["route_id"] == "fracciones_expresiones")
    assert fractions["total_concepts"] == 2
    assert fractions["progress"] == .65
    assert fractions["completed_concepts"] == 1
    assert all("title" in item and "progress" in item for item in routes)
