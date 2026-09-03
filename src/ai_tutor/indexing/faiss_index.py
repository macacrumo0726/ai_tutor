from __future__ import annotations
import numpy as np

class DenseIndex:
    """Exact cosine index; small and portable. Optional FAISS can replace it later."""
    def __init__(self, vectors: np.ndarray, ids: list[str]):
        self.vectors=np.asarray(vectors,dtype=np.float32); self.ids=ids
    def search(self, query: np.ndarray, top_k: int) -> list[tuple[str,float]]:
        # einsum avoids spurious Accelerate/BLAS overflow warnings observed on
        # finite, unit-normalized float32 arrays on the supported macOS/Py3.9 env.
        scores=np.einsum("ij,j->i",self.vectors,query.reshape(-1),optimize=False)
        order=np.argsort(-scores)[:top_k]
        return [(self.ids[i],float(scores[i])) for i in order]
