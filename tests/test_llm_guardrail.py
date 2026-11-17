from ai_tutor.assessment.llm_guardrail import parse_guardrail_review


def test_guardrail_parser_accepts_json_wrapper():
    result = parse_guardrail_review('```json\n{"valid": true, "reason": "tema correcto"}\n```')
    assert result.status == "accepted"


def test_guardrail_parser_rejects_invalid_response():
    result = parse_guardrail_review('{"valid": false, "reason": "respuesta fuera de tema"}')
    assert result.status == "rejected"
    assert "fuera" in result.reason


def test_guardrail_parser_fails_closed_for_unstructured_verdict():
    result = parse_guardrail_review("Sí, parece correcta")
    assert result.status == "unavailable"
