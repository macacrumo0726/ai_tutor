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
            client=OpenAI(
                base_url=self.base_url,
                api_key=os.getenv("LOCAL_LLM_API_KEY","ollama"),
                timeout=float(os.getenv("AI_TUTOR_PROVIDER_TIMEOUT_SECONDS", "20")),
                # A retry inside the provider blocks the application fallback
                # and multiplies latency under load. The API layer performs
                # the controlled fallback instead.
                max_retries=int(os.getenv("LOCAL_LLM_MAX_RETRIES", "0")),
            )
            # Qwen3 exposes an optional chain-of-thought stream.  The tutor must
            # receive only the final educational answer, never internal reasoning.
            # Ollama accepts ``think=false`` through the OpenAI-compatible
            # ``extra_body`` extension.
            response=client.chat.completions.create(
                model=self.model,
                # Qwen3 recognizes this control token and keeps its internal
                # reasoning out of the visible answer.  The API-level
                # ``think=false`` flag is also sent below for newer Ollama
                # releases; the token keeps compatibility with older ones.
                messages=[{"role":"user","content":"/no_think\n" + prompt}],
                temperature=0,
                max_tokens=int(os.getenv("LOCAL_LLM_MAX_TOKENS", "1024")),
                extra_body={"think": False},
            )
            message=response.choices[0].message
            text=message.content or ""
            # Some Ollama/Qwen combinations expose a separate ``reasoning``
            # field.  Never fall back to that field: it is internal chain of
            # thought and must not reach the student.  An empty final channel
            # is treated as a provider failure so the configured fallback can
            # answer instead.
            if not text.strip():
                raise RuntimeError("local model returned no final answer")
            return GenerationResult(text,"local_open_source",self.model,(perf_counter()-start)*1000)
        except Exception as exc:
            return GenerationResult("","local_open_source",self.model,(perf_counter()-start)*1000,False,str(exc))
