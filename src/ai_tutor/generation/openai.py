import os
from time import perf_counter
from .base import GenerationResult
class OpenAIGenerator:
    def __init__(self,model="gpt-4.1-mini"): self.model=model
    def generate(self,prompt):
        start=perf_counter()
        try:
            from openai import OpenAI
            text=OpenAI(api_key=os.environ["OPENAI_API_KEY"]).responses.create(model=self.model,input=prompt).output_text
            return GenerationResult(text,"openai",self.model,(perf_counter()-start)*1000)
        except Exception as exc: return GenerationResult("","openai",self.model,(perf_counter()-start)*1000,False,str(exc))

