import pytest

from ai_tutor.memory import AuthenticationService, ConversationRepository, LearningProfileService


@pytest.fixture
def services(tmp_path):
    repository = ConversationRepository(tmp_path / "research.sqlite3")
    return repository, AuthenticationService(repository, admin_ids="admin"), LearningProfileService(repository)


def test_registration_hashes_pin_and_login_creates_session(services):
    repository, auth, _ = services
    session = auth.register("student_01", "Student", "2468")
    stored = repository.get_user("student_01")
    assert stored["password_hash"] != "2468"
    assert stored["password_salt"]
    assert auth.require(session)["user_id"] == "student_01"
    assert auth.login("student_01", "2468")["authenticated"] is True
    with pytest.raises(ValueError, match="incorrecto"):
        auth.login("student_01", "0000")


def test_roles_are_allowlisted_and_admin_guard_is_enforced(services):
    _, auth, _ = services
    student = auth.register("student", "Student", "1234")
    administrator = auth.register("admin", "Administrator", "1234")
    assert auth.require(administrator, "admin")["role"] == "admin"
    with pytest.raises(PermissionError):
        auth.require(student, "admin")


def test_explicit_feedback_updates_mastery_and_preserves_evidence(services):
    repository, auth, learning = services
    auth.register("student", "Student", "1234")
    first = learning.record_feedback("student", ["factorization"], "understood")
    second = learning.record_feedback("student", ["factorization"], "needs_help")
    assert first["updates"][0]["mastery"] == pytest.approx(0.75)
    assert second["updates"][0]["mastery"] < first["updates"][0]["mastery"]
    report = repository.learning_report("student")
    assert len(report["evidence"]) == 2
    assert report["mastery"][0]["evidence_count"] == 2
    assert learning.state_for("student").profile_id == "persistent:student"


def test_feedback_requires_concepts_and_known_signal(services):
    _, auth, learning = services
    auth.register("student", "Student", "1234")
    with pytest.raises(ValueError, match="No hay conceptos"):
        learning.record_feedback("student", [], "understood")
    with pytest.raises(ValueError, match="Unknown feedback"):
        learning.record_feedback("student", ["functions"], "guessed")


def test_logout_invalidates_session(services):
    _, auth, _ = services
    session = auth.register("student", "Student", "1234")
    auth.logout(session)
    with pytest.raises(PermissionError):
        auth.require(session)


def test_conversation_confusion_updates_profile_with_lower_weight(services):
    repository, auth, learning = services
    auth.register("student", "Student", "1234")
    conversation=repository.create_conversation("student")
    repository.add_message("student",conversation.conversation_id,"assistant",
                           "¿Puedes decirme qué factor usarías?",{"concepts":["factorization"]})
    prior=repository.list_messages("student",conversation.conversation_id)
    result=learning.infer_from_response("student","No entiendo cómo hacerlo",prior,
                                        conversation.conversation_id)
    assert result["evidence_type"]=="confusion_report"
    assert result["weight"]==pytest.approx(.25)
    assert result["changes_mastery"] is True
    assert repository.get_mastery("student")[0]["mastery"] < .5


def test_unscored_math_reply_is_recorded_without_changing_mastery(services):
    repository, auth, learning = services
    auth.register("student", "Student", "1234")
    conversation=repository.create_conversation("student")
    repository.add_message("student",conversation.conversation_id,"assistant",
                           "¿Qué valor anula el denominador?",{"concepts":["domain"]})
    prior=repository.list_messages("student",conversation.conversation_id)
    result=learning.infer_from_response("student","x = 3",prior,conversation.conversation_id)
    mastery=repository.get_mastery("student")[0]
    assert result["evidence_type"]=="unscored_student_response"
    assert result["changes_mastery"] is False
    assert mastery["mastery"]==pytest.approx(.5)
    assert repository.learning_report("student")["evidence"][0]["source"]=="conversation_inference"


def test_self_report_is_separate_from_mastery_and_can_be_contrasted(services):
    repository, auth, _ = services
    auth.register("student", "Student", "1234")
    conversation=repository.create_conversation("student")
    repository.save_self_report("student",conversation.conversation_id,["domain"],"understood",1.0)
    assert repository.get_mastery("student")==[]
    repository.save_understanding_evaluation(
        "student",conversation.conversation_id,["domain"],"No entiendo","not_understood",
        .15,.85,{"confusion":True},"heuristic_v1")
    comparison=repository.latest_signal_comparison("student",conversation.conversation_id)
    assert comparison["status"]=="contradiction"
    assert comparison["direction"]=="self_report_higher"
    assert repository.get_mastery("student")==[]
