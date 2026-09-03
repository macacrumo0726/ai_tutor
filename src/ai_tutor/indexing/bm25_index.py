from __future__ import annotations
import math,re
from collections import Counter

def tokenize(text: str) -> list[str]: return re.findall(r"\w+",text.lower(),flags=re.UNICODE)

class BM25Index:
    def __init__(self,texts:list[str],ids:list[str],k1:float=1.5,b:float=.75):
        self.ids=ids; self.docs=[tokenize(t) for t in texts]; self.tf=[Counter(d) for d in self.docs]; self.k1=k1; self.b=b
        self.avgdl=sum(map(len,self.docs))/max(1,len(self.docs)); self.df=Counter()
        for doc in self.docs: self.df.update(set(doc))
    def search(self,query:str,top_k:int)->list[tuple[str,float]]:
        q=tokenize(query); n=len(self.docs); scored=[]
        for ident,doc,tf in zip(self.ids,self.docs,self.tf):
            score=0.0
            for term in q:
                freq=tf[term]; df=self.df[term]
                if not freq: continue
                idf=math.log(1+(n-df+.5)/(df+.5)); denom=freq+self.k1*(1-self.b+self.b*len(doc)/max(self.avgdl,1))
                score += idf*freq*(self.k1+1)/denom
            scored.append((ident,score))
        return sorted(scored,key=lambda x:(-x[1],x[0]))[:top_k]
