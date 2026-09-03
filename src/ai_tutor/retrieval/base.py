from __future__ import annotations
from dataclasses import dataclass,field
from typing import Any,Protocol

@dataclass
class RetrievedChunk:
    chunk_id:str; text:str; score:float; concept_ids:list[str]=field(default_factory=list); metadata:dict[str,Any]=field(default_factory=dict)

@dataclass
class RetrievalResult:
    query:str; chunks:list[RetrievedChunk]; concepts:list[str]; scores:list[float]
    metadata:dict[str,Any]; latency_ms:float; debug_info:dict[str,Any]

class BaseRetriever(Protocol):
    def retrieve(self,query:str,top_k:int=5,**kwargs)->RetrievalResult: ...

