from __future__ import annotations
import re


REFERENCE_TERMS = re.compile(r"\b(eso|esto|esa|ese|lo anterior|por qué|porque|entonces|ahí|ese valor|esa respuesta)\b", re.I)
SHORT_ANSWER = re.compile(r"^\s*(?:[a-z]\s*=\s*)?[-+]?\d+(?:[.,]\d+)?\s*$", re.I)


def needs_context(message: str) -> bool:
    words = re.findall(r"\w+", message, re.UNICODE)
    return len(words) <= 7 or bool(REFERENCE_TERMS.search(message)) or bool(SHORT_ANSWER.match(message))


def contextualize(message: str, previous_messages) -> str:
    """Create a standalone retrieval query without calling another LLM."""
    if not previous_messages or not needs_context(message):
        return message
    recent = previous_messages[-4:]
    context = "\n".join(f"{item.role}: {item.content}" for item in recent)
    return f"Contexto de la conversación:\n{context}\nMensaje actual del estudiante: {message}"


def format_history(summary: str, active_problem: str, messages, max_messages=8) -> str:
    lines = []
    if summary:
        lines.append(f"Resumen anterior: {summary}")
    if active_problem:
        lines.append(f"Problema activo: {active_problem}")
    if messages:
        lines.append("Últimos turnos:")
        lines.extend(f"{item.role}: {item.content}" for item in messages[-max_messages:])
    return "\n".join(lines) if lines else "No hay conversación previa."
