from __future__ import annotations
import os
from time import perf_counter
from .base import GenerationResult

class LocalOpenSourceGenerator:
    """OpenAI-compatible local inference (Ollama, vLLM, SGLang or LM Studio)."""
    def __init__(self,model:str,base_url:str): self.model=model; self.base_url=base_url
    def generate(self,prompt:str)->GenerationResult:
        start=perf_counter()
        try:
            from openai import OpenAI
            client=OpenAI(base_url=self.base_url,api_key=os.getenv("LOCAL_LLM_API_KEY","ollama"))
            response=client.chat.completions.create(model=self.model,messages=[{"role":"user","content":prompt}],temperature=0)
            text=response.choices[0].message.content or ""
            return GenerationResult(text,"local_open_source",self.model,(perf_counter()-start)*1000)
        except Exception as exc:
            return GenerationResult("","local_open_source",self.model,(perf_counter()-start)*1000,False,str(exc))
