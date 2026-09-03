from ai_tutor.evaluation.answer_metrics import exact_match,token_f1
from ai_tutor.evaluation.retrieval_metrics import hit_at_k,recall_at_k,mrr_at_k,ndcg_at_k,NOT_AVAILABLE

def test_answer_metrics():
    assert exact_match("La función", "la funcion")==1
    assert 0<token_f1("raíz cuadrada", "raíz")<1
def test_retrieval_metrics_and_missing_gold():
    assert hit_at_k(["a","b"],["b"],2)==1
    assert recall_at_k(["a"],["a","b"],1)==.5
    assert mrr_at_k(["x","a"],["a"],2)==.5
    assert ndcg_at_k(["a"],["a"],1)==1
    assert hit_at_k(["a"],[],1)==NOT_AVAILABLE

