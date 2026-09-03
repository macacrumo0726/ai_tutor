import os
from time import perf_counter
from .base import GenerationResult
class GeminiGenerator:
    def __init__(self,model="gemini-3.6-flash"):
        self.model=model
        self._client=None
    def generate(self,prompt):
        start=perf_counter()
        try:
            from google import genai
            # Keep a strong reference: constructing the client inline can close
            # its HTTP transport before the model call finishes.
            if self._client is None:
                self._client=genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            response=self._client.models.generate_content(model=self.model,contents=prompt)
            return GenerationResult(response.text or "","gemini",self.model,(perf_counter()-start)*1000)
        except Exception as exc:return GenerationResult("","gemini",self.model,(perf_counter()-start)*1000,False,str(exc))
