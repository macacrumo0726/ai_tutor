from ai_tutor.student_model import StudentState
from ai_tutor.retrieval.pep_plan_rag import PEPPlanRAGRetriever


def test_student_state_is_continuous_and_bounded():
    state = StudentState(profile_id="persistent:test", concept_mastery={"domain": 0.23})
    assert state.mastery_for("domain") == 0.23
    state.concept_mastery["domain"] = 4.0
    assert state.mastery_for("domain") == 1.0


def test_persistent_state_changes_gap_signal(baseline, graph):
    concepts=[{"concept_id":node,"canonical_name":node} for node in
              ("algebra","factorization","quadratic","domain","rational")]
    units=[{"concept_id":node,"common_misconceptions":[]} for node in
           ("algebra","factorization","quadratic","domain","rational")]
    config={"max_hops":2,"max_nodes":10,"max_iterations":3,"planning_max_depth":2,
            "planning_max_nodes":5,"utility_weights":{"direct":.4,"ppr":.2,"target":.1,
            "prerequisite_need":.1,"student_gap":.05,"misconception":.0,
            "instructional":.05,"activation":.1}}
    retriever = PEPPlanRAGRetriever(baseline,graph,concepts,units,config)
    low = StudentState(profile_id="low", default_mastery=0.1)
    high = StudentState(profile_id="high", default_mastery=0.9)
    low_result = retriever.retrieve("quadratic equations", top_k=3, student_state=low)
    high_result = retriever.retrieve("quadratic equations", top_k=3, student_state=high)
    assert len(low_result.debug_info["learning_path"]["missing_prerequisites"]) >= len(
        high_result.debug_info["learning_path"]["missing_prerequisites"]
    )
    assert low_result.debug_info["student_state"]["profile_id"] == "low"
