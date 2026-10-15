from __future__ import annotations

import os
import re
import time
import hashlib
from dataclasses import asdict
from threading import Lock
from typing import Optional

from ai_tutor.assessment import UnderstandingEvaluator, verify_short_math_response
from ai_tutor.generation.factory import create_generator
from ai_tutor.memory import AuthenticationService, ConversationMemory, ConversationRepository, LearningProfileService
from ai_tutor.tutoring.tutor import Tutor
from ai_tutor.utils.io import read_jsonl
from ai_tutor.utils.paths import load_config, project_path


def _bool_env(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def _student_text(text: str) -> str:
    text = re.sub(r"\\\((.*?)\\\)", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\\\[(.*?)\\\]", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\\)\$([^$\n]+)\$", r"\1", text)
    return text.replace(r"\$", "$").replace("`", "").strip()


SOCIAL_PATTERNS = {
    "greeting": re.compile(
        r"^\s*(?:¡?hola!?|buen(?:os|as)\s+(?:días|dias|tardes|noches)|hey|hi|qué tal|que tal)\s*[.!?]*\s*$",
        re.IGNORECASE,
    ),
    "thanks": re.compile(r"^\s*(?:gracias|muchas gracias|entendido|perfecto)\s*[.!?]*\s*$", re.IGNORECASE),
    "goodbye": re.compile(r"^\s*(?:adiós|adios|chao|hasta luego|nos vemos)\s*[.!?]*\s*$", re.IGNORECASE),
}


def _social_intent(message: str) -> Optional[str]:
    for intent, pattern in SOCIAL_PATTERNS.items():
        if pattern.fullmatch(message):
            return intent
    return None


class TutorApplicationService:
    """Application boundary shared by FastAPI and future cloud workers."""

    def __init__(self, repository=None):
        config = load_config()
        database_path = project_path(config["paths"]["conversations"])
        self.repository = repository or ConversationRepository(database_path)
        self.memory = ConversationMemory(self.repository, **config.get("memory", {}))
        self.auth = AuthenticationService(self.repository)
        self.learning = LearningProfileService(self.repository)
        self.understanding = UnderstandingEvaluator()
        concepts = read_jsonl(project_path(config["paths"]["concepts"]))
        self.concept_labels = {item["concept_id"]: item.get("concept_name", item["concept_id"]) for item in concepts}
        self.default_provider = os.getenv("AI_TUTOR_DEFAULT_PROVIDER", "gemini")
        self.default_retrieval = os.getenv("AI_TUTOR_DEFAULT_RETRIEVAL", "pep_plan_rag")
        self.allow_fallback = _bool_env("AI_TUTOR_ALLOW_MODEL_FALLBACK", True)
        self._tutors: dict[str, Tutor] = {}
        self._tutor_lock = Lock()
        self.protocol_pdf = project_path("data/protocol/Proyecto_doctoral_manejo_etico_de_datos.pdf")
        self.protocol_version = self._protocol_version()

    def _protocol_version(self):
        if not self.protocol_pdf.exists():
            return "2026-10-15-unavailable"
        digest = hashlib.sha256(self.protocol_pdf.read_bytes()).hexdigest()[:12]
        return f"2026-10-15-{digest}"

    def protocol_summary(self):
        return {
            "title": "Protocolo de manejo ético de datos",
            "version": self.protocol_version,
            "summary": (
                "El protocolo explica qué datos se recogerán en la investigación, cómo se obtendrán, "
                "cómo se almacenarán y quién podrá acceder a ellos. La participación es voluntaria; "
                "los registros se asocian a códigos seudónimos, se minimizan los datos y se aplican "
                "controles de seguridad, acceso por roles, revisión de conversaciones y retención limitada."
            ),
            "sections": [
                "Datos cuantitativos, cualitativos, técnicos y de caracterización amplia.",
                "Recolección posterior al aval ético y al consentimiento informado.",
                "Almacenamiento institucional con cifrado, respaldos y control de acceso.",
                "Acceso restringido al equipo autorizado y bajo mínimo privilegio.",
                "Conservación prevista de datos seudonimizados durante cinco años, salvo decisión ética o institucional distinta.",
                "Mitigación mediante minimización, seudonimización, auditoría y divulgación agregada.",
            ],
            "pdf_url": "/api/protocol/document",
        }

    def protocol_status(self, user_id: str):
        acceptance = self.repository.get_protocol_acceptance(user_id, self.protocol_version)
        latest = self.repository.get_protocol_acceptance(user_id)
        return {
            "current_version": self.protocol_version,
            "accepted_current": bool(acceptance and acceptance["accepted"]),
            "acceptance": acceptance,
            "latest_acceptance": latest,
        }

    def accept_protocol(self, user_id: str, version: str, accepted: bool):
        if version != self.protocol_version:
            raise ValueError("La versión del protocolo ya no está vigente")
        if not accepted:
            raise ValueError("Debes aceptar el protocolo para continuar")
        return self.repository.save_protocol_acceptance(user_id, version, accepted)

    def require_protocol(self, identity: dict):
        status = self.protocol_status(identity["user_id"])
        if not status["accepted_current"]:
            raise PermissionError("Debes aceptar el protocolo de datos vigente antes de continuar")
        return identity

    def session(self, token: str, role: Optional[str] = None):
        return self.auth.require({"token": token}, role)

    def tutor(self, provider: str):
        with self._tutor_lock:
            if provider not in self._tutors:
                self._tutors[provider] = Tutor(generator_provider=provider)
            return self._tutors[provider]

    def conversation_payload(self, conversation, include_messages=False):
        payload = asdict(conversation)
        if include_messages and conversation.messages is not None:
            payload["messages"] = [asdict(message) for message in conversation.messages]
        else:
            payload.pop("messages", None)
        return payload

    def ask(self, identity: dict, conversation_id: str, message: str):
        user_id = identity["user_id"]
        prepared = self.memory.prepare(user_id, conversation_id, message)
        social_intent = _social_intent(message)
        if social_intent:
            started = time.perf_counter()
            first_name = identity.get("display_name", "").strip().split(" ")[0] or "estudiante"
            answers = {
                "greeting": f"¡Hola, {first_name}! Soy PATI. ¿Qué tema o ejercicio de Precálculo quieres trabajar hoy?",
                "thanks": "¡Con gusto! Antes de seguir, ¿sientes que la idea quedó clara o quieres comprobarla con un ejemplo corto?",
                "goodbye": "¡Hasta luego! Cuando regreses podemos continuar desde esta misma conversación.",
            }
            metadata = {
                "intent": social_intent,
                "retrieval_method": "none",
                "model_provider": "conversation_router",
                "student_profile": f"persistent:{user_id}",
                "retrieval_query": message,
                "chunks": [],
                "concepts": [],
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "effective_model": "deterministic-social-router-v1",
                "fallback_used": False,
                "requested_provider": self.default_provider,
            }
            answer = answers[social_intent]
            self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
            return {"answer": answer, "metadata": metadata}

        profile = self.learning.state_for(user_id)
        prior_messages = prepared["messages"]
        previous_tutor = next((item for item in reversed(prior_messages) if item.role == "assistant"), None)
        verification = verify_short_math_response(
            message,
            previous_tutor.content if previous_tutor else "",
        )
        conversation_context = prepared["conversation_context"]
        if verification:
            verdict = "CORRECTA" if verification["status"] == "correct" else "INCORRECTA"
            conversation_context += (
                "\n\nVerificación matemática determinista del turno actual: "
                f"la respuesta {message!r} es {verdict}. "
                f"Valor esperado: {verification['expected_value']:g}. "
                f"Regla: {verification['explanation']}. "
                "Respeta esta verificación; no felicites una respuesta incorrecta."
            )
        elif previous_tutor and "?" in previous_tutor.content and len(message.strip()) <= 40:
            conversation_context += (
                "\n\nLa respuesta breve actual no tiene verificación automática disponible. "
                "No afirmes que es correcta sin comprobarla explícitamente dentro de tu respuesta."
            )
        provider = self.default_provider
        retrieval_method = self.default_retrieval
        response = None
        requested_error = ""
        primary_provider_error = ""
        model_fallback_used = False
        effective_provider = provider
        try:
            response = self.tutor(provider).ask(
                message,
                retrieval_method,
                knowledge_mode="instructional_database",
                student_profile=profile,
                conversation_context=conversation_context,
                retrieval_query=prepared["retrieval_query"],
            )
            requested_error = response.generation_error
            primary_provider_error = response.primary_generation_error
            model_fallback_used = response.model_fallback_used
        except Exception as exc:  # provider initialization/network error
            requested_error = str(exc)

        if (response is None or requested_error) and self.allow_fallback and provider != "instructional":
            effective_provider = "instructional"
            response = self.tutor("instructional").ask(
                message,
                retrieval_method,
                knowledge_mode="instructional_database",
                student_profile=profile,
                conversation_context=conversation_context,
                retrieval_query=prepared["retrieval_query"],
            )
        if response is None:
            raise RuntimeError(requested_error or "No fue posible generar una respuesta")

        concepts = list(response.retrieval.concepts)
        metadata = {
            "retrieval_method": retrieval_method,
            "model_provider": effective_provider,
            "student_profile": profile.profile_id,
            "retrieval_query": prepared["retrieval_query"],
            "chunks": [chunk.chunk_id for chunk in response.retrieval.chunks],
            "concepts": concepts,
            "latency_ms": round(response.total_latency_ms, 2),
            "effective_model": response.generation_model,
            "fallback_used": effective_provider != provider or model_fallback_used,
            "requested_provider": provider,
            "requested_provider_error": requested_error or primary_provider_error,
            "response_verification": verification or {"status": "not_available"},
        }
        answer = _student_text(response.answer)
        if verification and verification["status"] == "incorrect":
            student_value = verification["student_value"]
            expected_value = verification["expected_value"]
            answer = (
                f"Revisemos esa respuesta: si sustituyes x = {student_value:g}, "
                "el denominador no queda en cero. Para encontrar el valor que debemos excluir, "
                f"resolvemos {verification['explanation']}. Por eso el valor correcto es "
                f"x = {expected_value:g}, no {student_value:g}. "
                "¿Puedes comprobarlo sustituyendo ese valor en el denominador?"
            )
            metadata["answer_guardrail_used"] = True
        else:
            metadata["answer_guardrail_used"] = False
        previous_concepts = previous_tutor.metadata.get("concepts", []) if previous_tutor else concepts
        if verification:
            is_correct = verification["status"] == "correct"
            evaluation = {
                "classification": "understood" if is_correct else "not_understood",
                "score": 1.0 if is_correct else 0.0,
                "confidence": verification["confidence"],
                "features": verification,
            }
            for concept_id in previous_concepts[:5]:
                self.repository.add_learning_evidence(
                    user_id, concept_id, "verified_conversational_response",
                    evaluation["score"], "deterministic_math_verifier",
                    conversation_id, verification, verification["confidence"],
                )
        else:
            evaluation = self.understanding.evaluate(
                message,
                previous_tutor.content if previous_tutor else "",
                previous_concepts,
                self.concept_labels,
            )
            self.learning.infer_from_response(
                user_id, message, prior_messages, conversation_id, previous_concepts,
            )
        self.repository.save_understanding_evaluation(
            user_id,
            conversation_id,
            previous_concepts,
            message,
            evaluation["classification"],
            evaluation["score"],
            evaluation["confidence"],
            evaluation["features"],
            "deterministic_math_verifier_v1" if verification else "heuristic_v1",
        )
        self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
        return {"answer": answer, "metadata": metadata}

    def feedback(self, identity: dict, conversation_id: str, concept_ids: list[str], signal: str):
        if not concept_ids:
            messages = self.repository.list_messages(identity["user_id"], conversation_id)
            assistant = next((item for item in reversed(messages) if item.role == "assistant"), None)
            concept_ids = assistant.metadata.get("concepts", []) if assistant else []
        if not concept_ids:
            raise ValueError("No hay conceptos asociados a la respuesta")
        scores = {"understood": 1.0, "partial": 0.5, "needs_help": 0.0}
        self.repository.save_self_report(
            identity["user_id"], conversation_id, concept_ids, signal, scores[signal]
        )
        return {
            "saved": True,
            "signal": signal,
            "concept_ids": concept_ids,
            "changes_mastery": False,
            "comparison": self.repository.latest_signal_comparison(identity["user_id"], conversation_id),
        }
