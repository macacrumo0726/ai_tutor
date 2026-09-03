from __future__ import annotations
import re,unicodedata
from collections import Counter

def normalize_answer(text:str)->str:
    text=unicodedata.normalize("NFKD",str(text)).encode("ascii","ignore").decode().lower()
    return " ".join(re.findall(r"\w+",text))
def exact_match(prediction:str,gold:str)->float: return float(normalize_answer(prediction)==normalize_answer(gold))
def token_f1(prediction:str,gold:str)->float:
    p=normalize_answer(prediction).split(); g=normalize_answer(gold).split()
    if not p or not g: return float(p==g)
    overlap=sum((Counter(p)&Counter(g)).values())
    if not overlap:return 0.0
    precision=overlap/len(p); recall=overlap/len(g); return 2*precision*recall/(precision+recall)

