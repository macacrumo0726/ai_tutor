from __future__ import annotations
from typing import Protocol,Union
class PedagogicalEvaluator(Protocol):
    def evaluate(self,question:str,answer:str,metadata:dict)->dict[str,Union[float,str]]: ...
