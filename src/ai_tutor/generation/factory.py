from __future__ import annotations
import os
from ai_tutor.utils.paths import project_path,load_config
from .instructional import InstructionalGenerator
from .openai import OpenAIGenerator
from .gemini import GeminiGenerator
from .deepseek import DeepSeekGenerator
from .local_open_source import LocalOpenSourceGenerator

def load_dotenv():
    path=project_path(".env")
    if not path.exists(): return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line=raw.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        key,value=line.split("=",1); os.environ.setdefault(key.strip(),value.strip().strip('"').strip("'"))

def create_generator(provider="instructional"):
    load_dotenv(); cfg=load_config(); models=cfg["generation"].get("default_models",{})
    if provider=="instructional": return InstructionalGenerator()
    if provider in {"local_base","local_finetuned","local_deepseek_base","local_deepseek_finetuned"}:
        env_names={"local_base":"LOCAL_BASE_MODEL","local_finetuned":"LOCAL_FINETUNED_MODEL","local_deepseek_base":"LOCAL_DEEPSEEK_BASE_MODEL","local_deepseek_finetuned":"LOCAL_DEEPSEEK_FINETUNED_MODEL"}
        env_model=env_names[provider]
        model=os.getenv(env_model,models[provider])
        base_url=os.getenv("LOCAL_LLM_BASE_URL",cfg["generation"]["local_openai_base_url"])
        return LocalOpenSourceGenerator(model,base_url)
    if provider=="openai_finetuned":
        model=os.getenv("OPENAI_FINETUNED_MODEL","")
        if not os.getenv("OPENAI_API_KEY") or not model: raise ValueError("Faltan OPENAI_API_KEY u OPENAI_FINETUNED_MODEL en .env")
        return OpenAIGenerator(model)
    required={"openai":"OPENAI_API_KEY","gemini":"GEMINI_API_KEY","deepseek":"DEEPSEEK_API_KEY"}
    if provider not in required: raise ValueError(f"Unknown generator provider: {provider}")
    if not os.getenv(required[provider]): raise ValueError(f"Falta {required[provider]} en .env")
    return {"openai":OpenAIGenerator,"gemini":GeminiGenerator,"deepseek":DeepSeekGenerator}[provider](models[provider])
