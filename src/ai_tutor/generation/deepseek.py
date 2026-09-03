import os
from time import perf_counter
from .base import GenerationResult
class DeepSeekGenerator:
    def __init__(self,model="deepseek-chat"): self.model=model
    def generate(self,prompt):
        start=perf_counter()
        try:
            from openai import OpenAI
            response=OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"],base_url="https://api.deepseek.com").chat.completions.create(model=self.model,messages=[{"role":"user","content":prompt}],temperature=0)
            return GenerationResult(response.choices[0].message.content or "","deepseek",self.model,(perf_counter()-start)*1000)
        except Exception as exc:return GenerationResult("","deepseek",self.model,(perf_counter()-start)*1000,False,str(exc))
