from __future__ import annotations

import os
import re
from dataclasses import asdict
from threading import Lock
from typing import Optional

from ai_tutor.assessment import UnderstandingEvaluator
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
    return text.replace(r"\$", "$").strip()


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
        profile = self.learning.state_for(user_id)
        provider = self.default_provider
        retrieval_method = self.default_retrieval
        response = None
        requested_error = ""
        effective_provider = provider
        try:
            response = self.tutor(provider).ask(
                message,
                retrieval_method,
                knowledge_mode="instructional_database",
                student_profile=profile,
                conversation_context=prepared["conversation_context"],
                retrieval_query=prepared["retrieval_query"],
            )
            requested_error = response.generation_error
        except Exception as exc:  # provider initialization/network error
            requested_error = str(exc)

        if (response is None or requested_error) and self.allow_fallback and provider != "instructional":
            effective_provider = "instructional"
            response = self.tutor("instructional").ask(
                message,
                retrieval_method,
                knowledge_mode="instructional_database",
                student_profile=profile,
                conversation_context=prepared["conversation_context"],
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
            "fallback_used": effective_provider != provider,
            "requested_provider": provider,
        }
        answer = _student_text(response.answer)
        prior_messages = prepared["messages"]
        previous_tutor = next((item for item in reversed(prior_messages) if item.role == "assistant"), None)
        previous_concepts = previous_tutor.metadata.get("concepts", []) if previous_tutor else concepts
        evaluation = self.understanding.evaluate(
            message,
            previous_tutor.content if previous_tutor else "",
            previous_concepts,
            self.concept_labels,
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
            "heuristic_v1",
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
