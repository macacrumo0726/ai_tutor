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
    # An explicit topic switch must replace the previous anchor; otherwise a
    # short phrase such as "cambiemos a ecuaciones" is still retrieved against
    # the old domain/factorization problem.
    if re.search(r"\b(?:cambiemos|pasemos|vamos\s+a\s+ver|ahora\s+(?:veremos|estudiemos)|nuevo\s+tema)\b", message, re.IGNORECASE):
        return message
    # Use a compact topical anchor instead of the full assistant transcript.
    # Long pedagogical answers contain unrelated textbook terms and can move a
    # short follow-up to the wrong retrieval topic.
    anchor = active_problem.strip()
    if not anchor:
        user_messages = [item.content.strip() for item in previous_messages if item.role == "user" and item.content.strip()]
        anchor = user_messages[-1] if user_messages else ""
    # Keep the latest tutor question as a narrow local anchor. This is useful
    # for numeric micro-checks (for example, the student answers only ``7``)
    # without sending the entire transcript to retrieval.
    last_tutor = next((item.content.strip() for item in reversed(previous_messages)
                       if item.role == "assistant" and item.content.strip()), "")
    if last_tutor:
        last_tutor = last_tutor[-500:]
    if anchor:
        suffix = f"\nÚltima pregunta del tutor: {last_tutor}" if last_tutor else ""
        return f"Problema activo: {anchor}{suffix}\nRespuesta o referencia actual del estudiante: {message}"
    return message


def format_history(summary: str, active_problem: str, messages, max_messages=8, pedagogical_state=None) -> str:
    lines = []
    if summary:
        lines.append(f"Resumen anterior: {summary}")
    if active_problem:
        lines.append(f"Problema activo: {active_problem}")
    state = pedagogical_state or {}
    if state:
        compact_state = []
        for key, label in (("current_activity", "Actividad"), ("pending_kind", "Tipo de actividad"),
                           ("expected_response_type", "Respuesta esperada"), ("exercise_expression", "Ejercicio activo"),
                           ("next_action", "Siguiente acción")):
            value = state.get(key)
            if value:
                compact_state.append(f"{label}: {str(value)[:240]}")
        if state.get("pending_question"):
            compact_state.append(f"Pregunta pendiente: {str(state['pending_question'])[-320:]}")
        if compact_state:
            lines.append("Estado pedagógico actual: " + " | ".join(compact_state))
    if messages:
        lines.append("Últimos turnos:")
        recent = []
        for item in messages[-max_messages:]:
            content = re.sub(r"\s+", " ", item.content).strip()
            if recent and recent[-1] == f"{item.role}: {content}":
                continue
            recent.append(f"{item.role}: {content}")
        lines.extend(recent)
    return "\n".join(lines) if lines else "No hay conversación previa."
