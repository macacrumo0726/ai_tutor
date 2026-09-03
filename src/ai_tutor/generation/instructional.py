from __future__ import annotations
import re
from time import perf_counter
from .base import GenerationResult

class InstructionalGenerator:
    """Readable deterministic fallback; never pretends to be an LLM."""
    def generate(self,prompt:str)->GenerationResult:
        start=perf_counter()
        question=self._field(prompt,"Pregunta del estudiante:","<evidence>")
        evidence=self._field(prompt,"<evidence>","</evidence>")
        concepts=self._field(prompt,"Conceptos recuperados:","Prerrequisitos detectados:")
        prereqs=prompt.split("Prerrequisitos detectados:",1)[-1].strip()
        sentences=self._clean_sentences(evidence,question)
        idea=sentences[0] if sentences else "La evidencia disponible no contiene una explicación suficientemente clara."
        concept=(concepts.split(",")[0].strip() if concepts.strip() else "este tema")
        prior=(prereqs.split(",")[0].strip() if prereqs.strip() else "las definiciones y operaciones algebraicas relacionadas")
        text=(f"Entiendo que quieres trabajar con {concept}.\n\n"
              f"Antes de resolverlo, conviene recordar {prior}.\n\n"
              f"Idea clave: {idea}\n\n"
              "Podemos abordarlo así:\n"
              "1. Identifica qué información proporciona el problema y qué debes encontrar.\n"
              f"2. Relaciona esos datos con la definición o propiedad de {concept}.\n"
              "3. Ejecuta cada operación justificando el paso y verifica el resultado en el enunciado original.\n\n"
              f"Micro-check: ¿puedes decirme cuál de esos tres pasos es el que te causa dificultad en «{question.strip()}»?")
        return GenerationResult(text,"instructional","instructional-offline-v1",(perf_counter()-start)*1000)

    @staticmethod
    def _field(text,start,end):
        return text.rsplit(start,1)[-1].split(end,1)[0].strip() if start in text else ""
    @staticmethod
    def _clean_sentences(evidence,question):
        query=set(re.findall(r"[a-záéíóúñ]{4,}",question.lower()))
        candidates=[]
        for sentence in re.split(r"(?<=[.!?])\s+",evidence):
            sentence=" ".join(sentence.split()).strip()
            if not 45<=len(sentence)<=420: continue
            letters=sum(ch.isalpha() for ch in sentence); digits=sum(ch.isdigit() for ch in sentence)
            if letters<25 or digits>letters*.25 or "�" in sentence: continue
            score=sum(term in sentence.lower() for term in query)
            candidates.append((score,sentence))
        return [s for _,s in sorted(candidates,key=lambda x:-x[0])[:3]]
