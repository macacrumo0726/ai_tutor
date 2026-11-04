from __future__ import annotations
import re


REFERENCE_TERMS = re.compile(r"\b(eso|esto|esa|ese|lo anterior|por qué|porque|entonces|ahí|ese valor|esa respuesta)\b", re.I)
SHORT_ANSWER = re.compile(r"^\s*(?:[a-z]\s*=\s*)?[-+]?\d+(?:[.,]\d+)?\s*$", re.I)


def needs_context(message: str) -> bool:
    words = re.findall(r"\w+", message, re.UNICODE)
    return len(words) <= 7 or bool(REFERENCE_TERMS.search(message)) or bool(SHORT_ANSWER.match(message))


def contextualize(message: str, previous_messages, active_problem: str = "") -> str:
    """Create a standalone retrieval query without calling another LLM."""
    if not previous_messages or not needs_context(message):
        return message
    # Use a compact topical anchor instead of the full assistant transcript.
    # Long pedagogical answers contain unrelated textbook terms and can move a
    # short follow-up to the wrong retrieval topic.
    anchor = active_problem.strip()
    if not anchor:
        user_messages = [item.content.strip() for item in previous_messages if item.role == "user" and item.content.strip()]
        anchor = user_messages[-1] if user_messages else ""
    return f"Problema activo: {anchor}\nRespuesta o referencia actual del estudiante: {message}" if anchor else message


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
