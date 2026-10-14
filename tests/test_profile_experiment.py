from ai_tutor.experiments.profile_experiment import counterfactual_summary,simulated_profiles


def test_profiles_change_only_mastery_assumption_for_same_question():
    question={"gold_prerequisite_ids":["algebra"],"gold_concept_ids":["functions"]}
    profiles=simulated_profiles(question)
    assert profiles["prerequisite_gap"].concept_mastery["algebra"]==.10
    assert profiles["high_prerequisite_mastery"].concept_mastery["algebra"]==.90


def test_counterfactual_summary_detects_adaptation():
    rows=[]
    for method in ("rag","graph_rag","pep_plan_rag"):
        for profile,chunks,pre in (
            ("high_prerequisite_mastery",["a","b"],0.0),
            ("prerequisite_gap",["a","c"] if method=="pep_plan_rag" else ["a","b"],1.0 if method=="pep_plan_rag" else 0.0)):
            rows.append({"question_id":"q1","method":method,"profile":profile,
                         "chunk_ids":chunks,"prerequisite_recall":pre,
                         "prerequisite_context_share":pre,"concept_recall":1.0})
    summary={row["method"]:row for row in counterfactual_summary(rows)}
    assert summary["rag"]["chunk_jaccard_distance"]==0
    assert summary["pep_plan_rag"]["chunk_jaccard_distance"]>0
    assert summary["pep_plan_rag"]["prerequisite_recall_lift"]==1.0
