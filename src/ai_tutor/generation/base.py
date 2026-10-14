from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from typing import Optional

@dataclass
class GenerationResult:
    text:str
    provider:str
    model:str
    latency_ms:float
    success:bool=True
    error:Optional[str]=None
    fallback_used:bool=False
    primary_error:Optional[str]=None
    attempted_models:tuple=()

class Generator(Protocol):
    def generate(self,prompt:str)->GenerationResult: ...
