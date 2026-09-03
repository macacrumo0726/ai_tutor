from ai_tutor.experiments.batch import bootstrap_ci,robust_queries,summarize,summarize_generation
from ai_tutor.experiments.report import results_fragment

def test_batch_summary_ignores_not_available():
    rows=[{"method":"rag","hit_at_k":1.0,"concept_recall":1.0,"prerequisite_recall":"not_available","latency_ms":10.0},
          {"method":"rag","hit_at_k":0.0,"concept_recall":0.5,"prerequisite_recall":"not_available","latency_ms":20.0}]
    summary=summarize(rows)[0]
    assert summary["hit_at_k"]==0.5 and summary["latency_ms"]==15.0
    assert summary["prerequisite_recall"]=="not_available"

def test_robust_queries_keep_three_variants():
    variants=robust_queries("¿Qué es una función?")
    assert set(variants)=={"original","polite","informal"}

def test_bootstrap_and_html_report():
    low,high=bootstrap_ci([0,1,1],resamples=100)
    assert low<=high
    fragment=results_fragment({"run_id":"demo","split":"validation","retrieval_summary":[{"method":"rag","n":3,"hit_at_k":1.0,"concept_recall":.5,"prerequisite_recall":"not_available","latency_ms":10.0}]})
    assert "demo" in fragment and "rag" in fragment and "ablaciones" in fragment and "robustez" in fragment

def test_generation_summary_groups_conditions():
    rows=[{"condition":"rag","token_f1":.5,"latency_ms":10},{"condition":"rag","token_f1":1.0,"latency_ms":20}]
    summary=summarize_generation(rows)[0]
    assert summary["condition"]=="rag" and summary["token_f1"]==.75 and summary["errors"]==0
