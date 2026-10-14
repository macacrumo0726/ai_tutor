import sys
import types

from ai_tutor.generation.gemini import GeminiGenerator


class _Models:
    def __init__(self, outcomes):
        self.outcomes=list(outcomes)
        self.calls=[]

    def generate_content(self, model, contents):
        self.calls.append(model)
        outcome=self.outcomes.pop(0)
        if isinstance(outcome,Exception):
            raise outcome
        return types.SimpleNamespace(text=outcome)


def _install_fake_sdk(monkeypatch, models):
    client=types.SimpleNamespace(models=models)
    genai=types.SimpleNamespace(Client=lambda **kwargs: client)
    sdk=types.ModuleType("google")
    sdk.genai=genai
    monkeypatch.setitem(sys.modules,"google",sdk)
    monkeypatch.setitem(sys.modules,"google.genai",genai)
    monkeypatch.setitem(sys.modules,"google.genai.types",
                        types.SimpleNamespace(HttpOptions=lambda **kwargs: kwargs))
    return client


def test_gemini_uses_flash_lite_after_503(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","not-a-real-key")
    models=_Models([RuntimeError("503 UNAVAILABLE: high demand"),"respuesta"])
    generator=GeminiGenerator("gemini-3.6-flash",100,"gemini-2.5-flash-lite")
    generator._client=_install_fake_sdk(monkeypatch,models)
    result=generator.generate("hola")
    assert result.success is True
    assert result.model=="gemini-2.5-flash-lite"
    assert result.fallback_used is True
    assert result.attempted_models==("gemini-3.6-flash","gemini-2.5-flash-lite")
    assert models.calls==["gemini-3.6-flash","gemini-2.5-flash-lite"]


def test_gemini_does_not_fallback_on_authentication_error(monkeypatch):
    models=_Models([RuntimeError("401 invalid API key")])
    generator=GeminiGenerator("gemini-3.6-flash",100,"gemini-2.5-flash-lite")
    generator._client=types.SimpleNamespace(models=models)
    result=generator.generate("hola")
    assert result.success is False
    assert result.fallback_used is False
    assert models.calls==["gemini-3.6-flash"]
