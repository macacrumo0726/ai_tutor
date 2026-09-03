from time import perf_counter
from .base import GenerationResult

class ExtractiveGenerator:
    """Offline deterministic generator for tests and reproducible smoke runs."""
    def generate(self,prompt:str)->GenerationResult:
        start=perf_counter(); evidence=prompt.split("<evidence>")[-1].split("</evidence>")[0].strip()
        text="Según la evidencia recuperada: " + (evidence[:900] if evidence else "No hay evidencia suficiente para responder con seguridad.")
        return GenerationResult(text,"extractive","evidence-first",(perf_counter()-start)*1000)

