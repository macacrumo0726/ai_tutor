import pytest
from ai_tutor.experiments.registry import resolve_provider,validate_condition

def test_open_source_original_and_finetuned_are_distinct():
    assert resolve_provider("qwen3_8b","original")=="local_base"
    assert resolve_provider("qwen3_8b","finetuned")=="local_finetuned"

def test_gemini_finetuning_is_explicitly_unavailable():
    with pytest.raises(ValueError): resolve_provider("gemini","finetuned")

def test_retrieval_requires_instructional_database():
    with pytest.raises(ValueError): validate_condition("qwen3_8b","original","raw","rag")
    validate_condition("qwen3_8b","original","instructional_database","pep_sa_rag")
