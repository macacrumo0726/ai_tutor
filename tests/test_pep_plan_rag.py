from ai_tutor.planning.learning_path import build_learning_path
from ai_tutor.retrieval.pep_plan_rag import PEPPlanRAGRetriever
from ai_tutor.student_model import get_student_profile


def test_student_profiles_change_mastery_estimate():
    unknown=get_student_profile("unknown")
    gap=get_student_profile("algebra_gap")
    assert gap.mastery_for("factorization","factorización algebraica") < unknown.mastery_for("factorization")


def test_learning_path_is_bounded_and_student_aware(graph):
    state=get_student_profile("algebra_gap")
    path=build_learning_path(graph,["quadratic"],state,{"factorization":"factorización algebraica"},max_depth=2,max_nodes=3)
    assert path["ordered_concepts"][-1]=="quadratic"
    assert "factorization" in path["missing_prerequisites"]
    assert len(path["distances"])<=3


def test_pep_plan_v3_exposes_plan_and_common_result(baseline,graph):
    concepts=[{"concept_id":node,"canonical_name":node} for node in ("algebra","factorization","quadratic","domain","rational")]
    units=[{"concept_id":node,"common_misconceptions":[]} for node in ("algebra","factorization","quadratic","domain","rational")]
    config={"max_hops":2,"max_nodes":10,"max_iterations":3,"planning_max_depth":2,"planning_max_nodes":5,
            "utility_weights":{"direct":.4,"ppr":.2,"target":.1,"prerequisite_need":.1,"student_gap":.05,"misconception":.0,"instructional":.05,"activation":.1}}
    result=PEPPlanRAGRetriever(baseline,graph,concepts,units,config).retrieve("ecuación cuadrática",2,student_profile="algebra_gap")
    assert result.metadata["method"]=="pep_plan_rag"
    assert result.debug_info["pep_version"]=="v3"
    assert result.debug_info["tutorial_plan"]
    assert len(result.chunks)==2
