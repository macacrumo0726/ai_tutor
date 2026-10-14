import os
from time import perf_counter
from .base import GenerationResult
class GeminiGenerator:
    def __init__(self,model="gemini-3.6-flash",timeout_ms=30000,
                 fallback_model="gemini-2.5-flash-lite"):
        self.model=model
        self.fallback_model=fallback_model
        self.timeout_ms=int(timeout_ms)
        self._client=None

    @staticmethod
    def _is_temporary(error):
        message=str(error).lower()
        return any(marker in message for marker in (
            "503", "unavailable", "high demand", "timed out", "timeout",
            "read operation timed out", "temporarily overloaded"))

    def generate(self,prompt):
        start=perf_counter()
        try:
            # Keep a strong reference: constructing the client inline can close
            # its HTTP transport before the model call finishes.
            if self._client is None:
                from google import genai
                from google.genai import types
                self._client=genai.Client(
                    api_key=os.environ["GEMINI_API_KEY"],
                    http_options=types.HttpOptions(timeout=self.timeout_ms),
                )
            try:
                response=self._client.models.generate_content(model=self.model,contents=prompt)
                return GenerationResult(response.text or "","gemini",self.model,
                                        (perf_counter()-start)*1000,
                                        attempted_models=(self.model,))
            except Exception as primary_exc:
                if not self.fallback_model or not self._is_temporary(primary_exc):
                    raise
                try:
                    response=self._client.models.generate_content(
                        model=self.fallback_model,contents=prompt)
                    return GenerationResult(
                        response.text or "","gemini",self.fallback_model,
                        (perf_counter()-start)*1000,True,None,True,str(primary_exc),
                        (self.model,self.fallback_model))
                except Exception as fallback_exc:
                    return GenerationResult(
                        "","gemini",self.fallback_model,(perf_counter()-start)*1000,
                        False,str(fallback_exc),True,str(primary_exc),
                        (self.model,self.fallback_model))
        except Exception as exc:
            return GenerationResult("","gemini",self.model,(perf_counter()-start)*1000,
                                    False,str(exc),False,None,(self.model,))
