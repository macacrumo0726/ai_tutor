"""Run a deterministic 100-turn conversation/context validation locally.

This exercises memory, contextual query formation, PEP-Plan-RAG v3 and the
offline instructional generator without spending remote-model quota. Use a
small real-Qwen smoke test separately for generation latency.
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from ai_tutor.api.services import TutorApplicationService, _response_passes_guardrails
from ai_tutor.memory import ConversationRepository
from ai_tutor.utils.paths import project_path


BANK = [
    ("dominio", ["¿Cómo encuentro el dominio de una función racional?", "¿Qué valor debo excluir?", "¿Por qué?", "Dame un ejemplo sencillo."]),
    ("factorizacion", ["Ayúdame a factorizar x² - 5x + 6", "¿Qué números buscamos?", "¿Y eso cómo se comprueba?", "¿Cuáles son las raíces?"]),
    ("funciones", ["¿Cuál es la diferencia entre relación y función?", "¿Puedes explicarlo con un ejemplo?", "¿Y qué pasa con el dominio?", "¿Eso siempre se cumple?"]),
    ("lineales", ["¿Cómo encuentro la pendiente de una recta?", "La pendiente me dio -2", "¿Eso significa que baja?", "¿Cómo verifico el resultado?"]),
    ("cuadraticas", ["¿Cómo se resuelve una ecuación cuadrática?", "¿Cuándo uso la fórmula general?", "¿Qué significa el discriminante?", "Ponme una práctica corta."]),
    ("desigualdades", ["¿Cómo resuelvo una desigualdad lineal?", "¿Por qué cambia el signo?", "¿Y si multiplico por un número negativo?", "¿Cómo represento la solución?"]),
    ("logaritmos", ["¿Qué significa un logaritmo?", "¿Cuál es su relación con los exponentes?", "¿Puedes mostrar otro ejemplo?", "¿Qué restricción tiene el argumento?"]),
    ("trigonometria", ["¿Qué representa el seno de un ángulo?", "¿Y el coseno?", "¿Cómo uso el círculo unitario?", "¿Qué debería practicar primero?"]),
    ("vectores", ["¿Qué es el producto punto de vectores?", "¿Cómo se calcula con componentes?", "¿Qué significa que dé cero?", "¿Puedes darme dos vectores?"]),
    ("radicales", ["¿Cómo simplifico una expresión con radicales?", "¿Puedo sumar dos raíces distintas?", "¿Qué propiedad debo recordar?", "¿Cómo compruebo la respuesta?"]),
]


def main() -> None:
    rows = []
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="pati-validation-") as tmp:
        repository = ConversationRepository(Path(tmp) / "validation.sqlite3")
        service = TutorApplicationService(repository=repository)
        service.default_provider = "instructional"
        service.default_retrieval = "pep_plan_rag"
        user = service.auth.register("validation_100", "Validation Student", "1234")
        version = service._protocol_version()
        repository.save_protocol_acceptance(user["user_id"], version, True)
        identity = service.auth.require(user)

        for conversation_index, (topic, turns) in enumerate(BANK):
            conversation = service.memory.create(identity["user_id"], title=f"Validación {topic}")
            for turn_index in range(10):
                question = turns[turn_index % len(turns)]
                # Add two paraphrased turns per topic to test continuity without
                # relying on a fixed exact phrase.
                if turn_index >= len(turns):
                    question = f"{question} (continuemos con {topic})"
                t0 = time.perf_counter()
                try:
                    result = service.ask(identity, conversation.conversation_id, question)
                    answer = result["answer"]
                    valid, reason = _response_passes_guardrails(question, answer)
                    metadata = result["metadata"]
                except Exception as exc:
                    answer = ""
                    valid = False
                    reason = str(exc)
                    metadata = {}
                elapsed = round((time.perf_counter() - t0) * 1000, 2)
                rows.append({
                    "conversation_index": conversation_index + 1,
                    "turn": turn_index + 1,
                    "topic": topic,
                    "question": question,
                    "answer": answer,
                    "valid": valid,
                    "guardrail_reason": reason,
                    "retrieval_method": metadata.get("retrieval_method", "not_available"),
                    "model_provider": metadata.get("model_provider", "not_available"),
                    "concepts": metadata.get("concepts", []),
                    "latency_ms": elapsed,
                })

    output = project_path("data/evaluation/conversation_validation_100_results.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "total_turns": len(rows),
        "valid_turns": sum(row["valid"] for row in rows),
        "invalid_turns": sum(not row["valid"] for row in rows),
        "conversation_count": len(BANK),
        "retrieval_methods": sorted({row["retrieval_method"] for row in rows}),
        "providers": sorted({row["model_provider"] for row in rows}),
        "mean_latency_ms": round(sum(row["latency_ms"] for row in rows) / len(rows), 2),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "rows": rows,
    }
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "rows"}, ensure_ascii=False, indent=2))
    print(f"Resultados detallados: {output}")


if __name__ == "__main__":
    main()
