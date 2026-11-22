#!/usr/bin/env python3
"""Regression bank for conversational continuity and short-answer handling.

Runs the real application service with the deterministic local generator so the
test isolates memory, contextual retrieval, verification and guardrails without
spending provider quota. It intentionally uses terse student turns.
"""
from __future__ import annotations

import json
import re
import tempfile
import time
from pathlib import Path

from ai_tutor.api.services import TutorApplicationService, _response_has_prompt_leak
from ai_tutor.memory import ConversationRepository
from ai_tutor.utils.paths import project_path


SCENARIOS = [
    {"name": "matrices_microcheck", "topic": "matrices", "turns": [
        "Quiero repasar suma, resta y multiplicación por escalares de matrices",
        "explícame el tema", "ejemplo práctico", "que sean iguales",
        "sumar las dos esquinas superiores izquierdas", "7", "¿y la siguiente entrada?",
    ]},
    {"name": "matrices_wrong_number", "topic": "matrices", "turns": [
        "Repasemos la suma de matrices", "Si tenemos 4 y 3 en la misma posición, ¿qué da?", "8",
        "ahora sí", "7",
    ]},
    {"name": "factorization_correction", "topic": "factor", "turns": [
        "Ayúdame a factorizar x² - 5x + 6", "4 y 6", "¿son correctos?", "-2 y -3", "¿cuáles son las raíces?",
    ]},
    {"name": "domain_numeric", "topic": "dominio", "turns": [
        "Encuentra el dominio de 1/(x-5)", "8", "¿por qué?", "5", "¿cómo lo escribo?",
    ]},
    {"name": "vectors_not_interest", "topic": "vector", "turns": [
        "Explícame el producto punto de vectores", "¿qué significa si da cero?", "dame un ejemplo", "(1,2) y (3,4)",
    ]},
    {"name": "functions_reference", "topic": "función", "turns": [
        "¿Cuál es la diferencia entre relación y función?", "explícalo con pares", "¿eso siempre se cumple?", "sí", "otro ejemplo",
    ]},
    {"name": "linear_slope", "topic": "pendiente", "turns": [
        "¿Cómo encuentro la pendiente de una recta?", "-2", "¿eso significa que baja?", "sí", "¿cómo verifico el resultado?",
    ]},
    {"name": "topic_switch", "topic": "logaritmo", "turns": [
        "Quiero estudiar factorización", "cambiemos a logaritmos", "¿qué es un logaritmo?", "¿y eso?", "un ejemplo",
    ]},
    {"name": "social_and_open", "topic": "dominio", "turns": [
        "hola", "¿qué me puedes explicar?", "dominio", "gracias", "continuemos",
    ]},
    {"name": "short_references", "topic": "desigualdad", "turns": [
        "¿Cómo resuelvo 2x+1<5?", "¿por qué?", "eso", "ejemplo", "-2",
    ]},
    {"name": "radicals", "topic": "radical", "turns": [
        "¿Cómo simplifico √12?", "¿qué propiedad uso?", "¿puedo sumar raíces?", "no entiendo eso", "otro caso",
    ]},
    {"name": "trigonometry", "topic": "seno", "turns": [
        "¿Qué representa el seno?", "¿y el coseno?", "¿eso depende del ángulo?", "sí", "círculo unitario",
    ]},
    {"name": "matrix_dimension_error", "topic": "matrices", "turns": [
        "¿Se pueden sumar una matriz 2x3 y una 3x2?", "no", "¿por qué?", "porque no son iguales", "otro ejemplo",
    ]},
    {"name": "matrix_scalar", "topic": "matrices", "turns": [
        "¿Cómo multiplico una matriz por un escalar?", "por cada entrada", "¿también cambia la dimensión?", "no", "explícame eso",
    ]},
    {"name": "quadratic_wrong_short", "topic": "cuadrática", "turns": [
        "Resuelve x² - 5x + 6 = 0", "4", "no entiendo", "factorización", "2 y 3",
    ]},
    {"name": "domain_change", "topic": "dominio", "turns": [
        "Halla el dominio de (x+1)/(x²-4)", "2 y -2", "¿los dos se excluyen?", "sí", "¿cómo lo escribo en intervalos?",
    ]},
    {"name": "function_yes_no", "topic": "función", "turns": [
        "¿{(1,2),(1,3)} es una función?", "no", "¿por qué?", "una entrada tiene dos salidas", "correcto",
    ]},
    {"name": "function_two_outputs", "topic": "función", "turns": [
        "¿Cuál es la diferencia entre relación y función?", "5", "¿sería función si una entrada tiene dos salidas?", "no", "¿por qué?",
    ]},
    {"name": "function_notation", "topic": "función", "turns": [
        "Si f(x)=2x+1, calcula f(3)", "7", "¿por qué sustituyes 3?", "porque x vale 3", "otro valor",
    ]},
    {"name": "slope_sign", "topic": "pendiente", "turns": [
        "Una recta pasa por (1,2) y (3,6), ¿cuál es la pendiente?", "2", "¿es positiva?", "sí", "¿qué significa?",
    ]},
    {"name": "inequality_flip", "topic": "desigualdad", "turns": [
        "Resuelve -2x > 6", "divido entre -2", "¿qué ocurre con el signo?", "se invierte", "x < -3",
    ]},
    {"name": "log_domain", "topic": "logaritmo", "turns": [
        "¿Cuál es el dominio de log(x-2)?", "x debe ser mayor que 2", "¿por qué?", "el argumento debe ser positivo", "ejemplo",
    ]},
    {"name": "radical_domain", "topic": "radical", "turns": [
        "¿Qué condición tiene √(x-1)?", "x mayor o igual que 1", "¿eso es el dominio?", "sí", "¿y si fuera raíz cúbica?",
    ]},
    {"name": "vector_orthogonal", "topic": "vector", "turns": [
        "Si el producto punto es cero, ¿qué significa?", "son perpendiculares", "¿siempre?", "en vectores no nulos", "dame un ejemplo",
    ]},
    {"name": "trig_short", "topic": "seno", "turns": [
        "¿Cuánto vale sen(0)?", "0", "¿y cos(0)?", "1", "¿por qué?",
    ]},
    {"name": "explicit_topic_switch", "topic": "ecuación", "turns": [
        "Ayúdame con el dominio", "ahora cambiemos a ecuaciones lineales", "resuelve 2x+4=10", "3", "compruébalo",
    ]},
    {"name": "ambiguous_references", "topic": "factor", "turns": [
        "Factoriza x²+3x", "no sé", "eso", "¿qué?", "dame una pista",
    ]},
    {"name": "conversation_reset", "topic": "función", "turns": [
        "hola", "quiero estudiar funciones", "nueva conversación", "¿qué es una función?", "gracias",
    ]},
    # Casos sintéticos informados por ejercicios abiertos de OpenStax/LibreTexts.
    # No reproducen conversaciones reales; representan errores frecuentes y
    # respuestas breves que suelen romper el seguimiento del contexto.
    {"name": "rational_domain_exclusion", "topic": "dominio", "turns": [
        "Halla el dominio de (x+1)/(x-2)", "2", "¿se incluye el 2?", "no", "¿cómo lo expreso?",
    ]},
    {"name": "radical_absolute_value", "topic": "radical", "turns": [
        "Simplifica √(x²)", "x", "¿siempre?", "no", "depende del signo de x",
    ]},
    {"name": "log_argument_positive", "topic": "logaritmo", "turns": [
        "¿Qué condición debe cumplir el argumento de log(x+3)?", "ser mayor que cero", "¿entonces x?", "> -3", "correcto",
    ]},
    {"name": "inequality_negative_divisor", "topic": "desigualdad", "turns": [
        "Resuelve -3x ≤ 12", "divido entre -3", "¿mantengo el signo?", "no, se invierte", "x ≥ -4",
    ]},
    {"name": "composition_context", "topic": "composición", "turns": [
        "Si f(x)=2x+1 y g(x)=x², calcula f(g(2))", "g(2)=4", "¿y luego?", "f(4)=9", "9",
    ]},
    {"name": "inverse_one_to_one", "topic": "inversa", "turns": [
        "¿Cuándo una función tiene inversa?", "cuando es uno a uno", "¿qué significa?", "cada salida proviene de una sola entrada", "¿cómo se verifica?",
    ]},
    {"name": "exponent_product_rule", "topic": "exponentes", "turns": [
        "Simplifica x³·x²", "x⁵", "¿se suman los exponentes?", "sí", "¿y x³+x²?",
    ]},
    {"name": "trig_degrees", "topic": "trigonometría", "turns": [
        "¿Cuánto vale sen(30°)?", "1/2", "¿y si el ángulo está en radianes?", "hay que convertir o interpretar la unidad", "explícame",
    ]},
    {"name": "quadratic_signs", "topic": "cuadrática", "turns": [
        "Factoriza x²+5x+6", "2 y 3", "¿qué signos deben tener?", "ambos positivos", "¿por qué?",
    ]},
    {"name": "matrix_scalar_followup", "topic": "matrices", "turns": [
        "Multiplica por 3 la matriz [[1,2],[0,-1]]", "[[3,6],[0,-3]]", "¿cambia su dimensión?", "no", "¿por qué?",
    ]},
]


def check_answer(question: str, answer: str, topic: str, metadata: dict) -> list[str]:
    failures = []
    if not answer.strip():
        failures.append("empty_answer")
    if _response_has_prompt_leak(answer):
        failures.append("prompt_leak")
    lowered = answer.lower()
    if topic == "matrices" and any(term in lowered for term in ("topografía", "ley de senos", "cosecante")):
        failures.append("matrix_wrong_topic")
    if topic == "vector" and any(term in lowered for term in ("interés continuo", "capital invertido", "topografía")):
        failures.append("vector_wrong_topic")
    if topic == "logaritmo" and "factoriz" in lowered and "logarit" not in lowered:
        failures.append("topic_switch_not_respected")
    if len(question.split()) <= 3 and not metadata.get("retrieval_query"):
        failures.append("missing_contextual_query")
    return failures


def main() -> None:
    started = time.perf_counter()
    rows = []
    with tempfile.TemporaryDirectory(prefix="pati-context-regressions-") as tmp:
        repository = ConversationRepository(Path(tmp) / "regressions.sqlite3")
        service = TutorApplicationService(repository=repository)
        service.default_provider = "instructional"
        service.default_retrieval = "pep_plan_rag"
        user = service.auth.register("context_regression", "Context Student", "1234")
        repository.save_protocol_acceptance(user["user_id"], service._protocol_version(), True)
        identity = service.auth.require(user)
        for scenario in SCENARIOS:
            conversation = service.memory.create(identity["user_id"], title=scenario["name"])
            for turn, question in enumerate(scenario["turns"], 1):
                started_turn = time.perf_counter()
                try:
                    result = service.ask(identity, conversation.conversation_id, question)
                    answer = result["answer"]
                    metadata = result["metadata"]
                    failures = check_answer(question, answer, scenario["topic"], metadata)
                    verification = metadata.get("response_verification", {})
                except Exception as exc:  # pragma: no cover - report unexpected regressions
                    answer, metadata, verification = "", {}, {}
                    failures = [f"exception:{type(exc).__name__}:{exc}"]
                rows.append({
                    "scenario": scenario["name"], "turn": turn, "topic": scenario["topic"],
                    "question": question, "answer": answer, "failures": failures,
                    "retrieval_query": metadata.get("retrieval_query", ""),
                    "concepts": metadata.get("concepts", []),
                    "verification": verification,
                    "provider": metadata.get("model_provider", ""),
                    "latency_ms": round((time.perf_counter() - started_turn) * 1000, 2),
                })
    output = project_path("data/evaluation/context_regression_results.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "scenario_count": len(SCENARIOS), "turn_count": len(rows),
        "failed_turns": sum(bool(row["failures"]) for row in rows),
        "failure_counts": {
            key: sum(key in failure for row in rows for failure in row["failures"])
            for key in sorted({failure.split(":", 1)[0] for row in rows for failure in row["failures"]})
        },
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2), "rows": rows,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False, indent=2))
    print(f"Resultados detallados: {output}")


if __name__ == "__main__":
    main()
