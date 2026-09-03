from functools import lru_cache
from hashlib import sha256

def cache_key(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()

cached = lru_cache(maxsize=2048)

