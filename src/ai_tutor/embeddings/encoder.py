from __future__ import annotations
import hashlib
import re
import numpy as np

class HashingEncoder:
    """Deterministic, offline encoder used as reproducible default."""
    def __init__(self, dimensions: int = 768): self.dimensions = dimensions
    def encode(self, texts: list[str]) -> np.ndarray:
        matrix=np.zeros((len(texts),self.dimensions),dtype=np.float32)
        for i,text in enumerate(texts):
            for token in re.findall(r"\w+",text.lower(),flags=re.UNICODE):
                digest=hashlib.blake2b(token.encode(),digest_size=8).digest()
                value=int.from_bytes(digest,"little"); matrix[i,value%self.dimensions] += 1 if value>>63 else -1
        norms=np.linalg.norm(matrix,axis=1,keepdims=True); norms[norms==0]=1
        return matrix/norms

