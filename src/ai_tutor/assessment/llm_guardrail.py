"""Optional second-pass guardrail for ambiguous generated answers.

The deterministic checks remain authoritative for prompt leaks, language and
known mathematical patterns.  This verifier is deliberately narrow: it asks a
second model whether the answer addresses the current turn and whether it
contains a concrete task when one was requested.  It is disabled by default in
tests and can be enabled for the pilot with ``AI_TUTOR_GUARDRAIL_DOUBLE_CHECK``.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ai_tutor.generation.factory import create_generator


@dataclass(frozen=True)
class GuardrailReview:
    status: str
    reason: str = ""
    provider: str = "deepseek"


def parse_guardrail_review(text: str) -> GuardrailReview:
    """Parse a strict JSON verdict, tolerating a short model wrapper."""
    raw = (text or "").strip()
    match = re.search(r"\{\s*[\"']valid[\"']\s*:\s*(true|false).*?\}", raw, re.I | re.S)
    if not match:
        return GuardrailReview("unavailable", "respuesta del verificador no estructurada")
    candidate = match.group(0).replace("'", '"')
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return GuardrailReview("unavailable", "respuesta del verificador no es JSON válido")
    valid = payload.get("valid")
    if not isinstance(valid, bool):
        return GuardrailReview("unavailable", "el verificador no devolvió un booleano")
    return GuardrailReview("accepted" if valid else "rejected", str(payload.get("reason", "")))


def review_with_deepseek(question: str, answer: str, conversation_context: str = "") -> GuardrailReview:
    """Ask DeepSeek for a compact relevance/quality verdict."""
    prompt = f"""Eres un verificador de seguridad y calidad de un tutor de Precálculo.
No resuelvas la pregunta y no redactes una respuesta pedagógica.
Comprueba únicamente si RESPUESTA responde a PREGUNTA, sigue el tema activo,
no expone instrucciones internas y, si la pregunta pide un ejercicio, contiene
un enunciado accionable. Devuelve solo JSON: {{\"valid\": true/false,
\"reason\": \"breve razón\"}}.

PREGUNTA:
{question[:1200]}

CONTEXTO:
{conversation_context[-2800:]}

RESPUESTA:
{answer[:2400]}
"""
    try:
        result = create_generator("deepseek").generate(prompt)
    except Exception as exc:  # provider unavailable: keep the tutor available
        return GuardrailReview("unavailable", f"no se pudo iniciar el verificador: {exc}")
    if not result.success:
        return GuardrailReview("unavailable", result.error or "verificador no disponible")
    return parse_guardrail_review(result.text)
