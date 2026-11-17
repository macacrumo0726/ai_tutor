from __future__ import annotations

import os
import re
import time
import hashlib
import networkx as nx
from dataclasses import asdict
from threading import Lock
from typing import Optional

from ai_tutor.assessment import UnderstandingEvaluator, verify_short_math_response
from ai_tutor.assessment.llm_guardrail import review_with_deepseek
from ai_tutor.generation.factory import create_generator
from ai_tutor.generation.instructional import InstructionalGenerator
from ai_tutor.memory import AuthenticationService, ConversationMemory, ConversationRepository, LearningProfileService
from ai_tutor.tutoring.tutor import Tutor, TutorResponse
from ai_tutor.retrieval.base import RetrievalResult
from ai_tutor.utils.io import read_jsonl
from ai_tutor.utils.paths import load_config, project_path
from ai_tutor.planning import build_learning_path
from ai_tutor.planning.learning_routes import build_learning_routes
from ai_tutor.conversation import route_turn


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
    "acknowledgement": re.compile(r"^\s*(?:ahora\s+s[ií]|s[ií]|correcto|exacto|vale|ok|de acuerdo|entendido)\s*[.!?]*\s*$", re.IGNORECASE),
}

# Confirmaciones de avance.  Se evalúan contra el estado pendiente antes del
# router social: ``correcto``, ``siguiente`` o ``verificado`` pueden ser la
# respuesta a una comprobación y no un saludo aislado.  La forma completa y
# la evidencia de cálculo permiten cubrir variantes como ``sí, me da 0`` sin
# mantener una lista de ejercicios concretos.
PROGRESS_ACK_PATTERN = re.compile(
    r"^\s*(?:s[ií]|correcto|exacto|vale|ok|de acuerdo|entendido|listo|"
    r"siguiente|verificad[oa]s?|comprobad[oa]s?|ya est[aá]|perfecto)\s*[.!?]*\s*$",
    re.IGNORECASE,
)
PROGRESS_EVIDENCE_PATTERN = re.compile(
    r"(?:verificad|comprobad|resultado\s+(?:es|da)\s+cero|(?:me|nos)\s+da\s+0|da\s+0\b|"
    r"queda\s+(?:listo|claro)|ya\s+est[aá])",
    re.IGNORECASE,
)
PROGRESS_NEGATION_PATTERN = re.compile(
    r"\bno\s+(?:me\s+)?(?:da|dio)\s+(?:0|cero)|(?:no|nunca)\s+(?:est[aá]\s+)?verificad",
    re.IGNORECASE,
)

OPEN_QUESTION_PATTERN = re.compile(
    r"^\s*[¿?]?(?:qué|que)\s+(?:me\s+)?puedes\s+(?:explicar|enseñar)(?:me)?\s*[?!.]*\s*$",
    re.IGNORECASE,
)


def _social_intent(message: str) -> Optional[str]:
    for intent, pattern in SOCIAL_PATTERNS.items():
        if pattern.fullmatch(message):
            return intent
    return None


def _open_question(message: str) -> bool:
    """Recognize a topic-free request before sending it to retrieval."""
    return bool(OPEN_QUESTION_PATTERN.fullmatch(message or ""))


def _is_progress_confirmation(message: str, state: dict | None) -> bool:
    """Return whether a short turn closes the currently pending step."""
    state = state or {}
    if not state.get("pending_question"):
        return False
    text = re.sub(r"\s+", " ", message or "").strip()
    if PROGRESS_NEGATION_PATTERN.search(text):
        return False
    return bool(PROGRESS_ACK_PATTERN.fullmatch(text) or PROGRESS_EVIDENCE_PATTERN.search(text))


def _pending_action_intent(message: str, state: dict | None) -> Optional[str]:
    """Interpret an affirmative answer to the action PATI just offered."""
    state = state or {}
    pending = state.get("pending_question", "")
    normalized = re.sub(r"\s+", " ", message or "").strip().lower()
    if not pending or not re.fullmatch(r"(?:s[ií]|correcto|vale|ok|de acuerdo|adelante)", normalized):
        return None
    if re.search(r"comprob|verific|sustituy|ra[ií]ces|c[aá]lculo", pending, re.I):
        return "continue_verification"
    return None


def _verification_roots(active_problem: str, pending: str = "") -> list[str]:
    from ai_tutor.generation.instructional import InstructionalGenerator

    roots = re.findall(r"x\s*=\s*(-?\d+(?:\.\d+)?)", pending or "")
    if len(roots) >= 2:
        return list(dict.fromkeys(roots))
    factorization = InstructionalGenerator._factor_quadratic(active_problem or "")
    return list(dict.fromkeys(re.findall(r"x\s*=\s*(-?\d+(?:\.\d+)?)", factorization)))


def _verification_step(active_problem: str, state: dict | None = None) -> tuple[str, list[str], int]:
    """Create the next concrete micro-check from the active problem/state."""
    state = state or {}
    roots = list(state.get("verification_roots") or [])
    if not roots:
        roots = _verification_roots(active_problem, state.get("pending_question", ""))
    index = int(state.get("verification_index", 0))
    index = min(index, max(0, len(roots) - 1))
    topic = active_problem or "el ejercicio"
    if roots and re.search(r"factor|cuadr[aá]tic|x\s*\^?2", topic + " " + str(state), re.I):
        root = roots[index]
        return (
            f"Comprobemos x = {root}. Sustitúyelo en el polinomio original: "
            f"{root}² - 5·{root} + 6. ¿Qué resultado obtienes?",
            roots,
            index,
        )
    return ("Hagamos la comprobación pendiente. Realiza el cálculo indicado y dime qué resultado obtienes.", roots, index)


def _pending_decline(message: str, state: dict | None) -> bool:
    state = state or {}
    pending = state.get("pending_question", "")
    return bool(
        state.get("expected_response_type") == "student_choice"
        and re.fullmatch(r"\s*(?:no|ahora no|prefiero no|más tarde)\s*[.!?]*", message or "", re.I)
        and re.search(r"(?:practic|repasar|otro\s+concepto|otro\s+ejercicio|siguiente\s+ejercicio|continuar)", pending, re.I)
    )


def _pending_activity_intent(message: str, previous_messages) -> Optional[str]:
    """Interpret a short turn against the tutor's pending pedagogical question.

    This runs before the social router: ``sí`` is not merely an acknowledgement
    when PATI just asked whether the learner wants an exercise.
    """
    latest = next((item.content for item in reversed(previous_messages) if item.role == "assistant"), "")
    if not latest:
        return None
    normalized = re.sub(r"\s+", " ", message or "").strip().lower()
    if re.search(r"explicaci[oó]n.*ejercicio|ejercicio.*explicaci[oó]n|expresi[oó]n.*paso", latest, re.I):
        if re.fullmatch(r"ejercicio|ejemplo|pr[aá]ctica|problema", normalized):
            return "exercise_request"
        if re.fullmatch(r"s[ií]|correcto|vale|ok|de acuerdo", normalized):
            return "exercise_confirmation"
    if re.search(r"¿?quieres que (?:probemos|trabajemos|hagamos).*\?|ejercicio.*\?", latest, re.I):
        if re.search(r"(?:dame|ponme|prop[oó]n|quiero)\s+(?:otro\s+|un\s+|una\s+)?(?:ejercicio|problema|pr[aá]ctica)", normalized):
            return "exercise_request"
        if re.fullmatch(r"s[ií]|correcto|vale|ok|de acuerdo", normalized):
            return "exercise_confirmation"
        if re.fullmatch(r"no|ahora no", normalized):
            return "decline_activity"
    if re.search(r"alguna parte|qu[eé] te gustar[ií]a|por d[oó]nde.*practicar|qu[eé].*practic|quieres empezar|con qu[eé].*empez", latest, re.I):
        # Accept both accented and unaccented variants. These are choices,
        # not new study topics: the learner is asking PATI to decide where to
        # begin within the active topic.
        if re.fullmatch(r"(?:no[, ]*)?(?:dime t[uú]|t[uú] dime|elige t[uú]|t[uú] elige|t[uú] decide|decide t[uú]|lo que sea|lo que (?:t[uú] )?(?:quieras|prefieras)|como (?:t[uú] )?(?:quieras|prefieras)|escoge t[uú]|elige por m[ií]|d[áa]mela t[uú]|dame la (?:pregunta|actividad|pr[aá]ctica)|dame un (?:ejercicio|ejemplo)|ponme (?:un )?(?:ejercicio|ejemplo)|prop[oó]n (?:un )?(?:ejercicio|ejemplo))", normalized):
            return "choose_for_student"
    return None


def _exercise_for_topic(active_problem: str) -> str:
    topic = (active_problem or "").lower()
    if re.search(r"exponente|radical", topic):
        return ("Perfecto. Empecemos con un ejercicio breve: simplifica 2³ · 2². "
                "¿Qué regla de exponentes usarías y cuál es el resultado?")
    if re.search(r"funci[oó]n", topic):
        return "Perfecto. Para practicar, si f(x) = 2x + 3, calcula f(4) y explícame qué sustituiste."
    if re.search(r"factor|cuadr[aá]tic", topic):
        return "Perfecto. Practiquemos: factoriza x² + 5x + 6. Busca dos números cuyo producto sea 6 y cuya suma sea 5."
    if re.search(r"dominio|racional", topic):
        return "Perfecto. Encuentra el dominio de f(x) = 1/(x - 4). ¿Qué valor hace cero el denominador?"
    if re.search(r"matriz", topic):
        return "Perfecto. Si A = [[1, 2], [3, 4]], calcula 2A. ¿Qué ocurre con cada entrada?"
    return "Perfecto. Propongo un ejercicio guiado sobre este tema. Escríbeme el primer paso que intentarías y lo revisamos juntos."


def _starting_point_for_topic(active_problem: str) -> str:
    topic = (active_problem or "").lower()
    if re.search(r"exponente", topic):
        return ("Yo empezaría por distinguir exponentes positivos, cero y negativos. "
                "Por ejemplo, a⁻² = 1/a² cuando a ≠ 0. Después podemos practicar una expresión corta.")
    if re.search(r"radical", topic):
        return "Yo empezaría por revisar cómo se simplifica una raíz usando factores cuadrados perfectos, como √12 = 2√3."
    if re.search(r"dominio|racional", topic):
        return ("Yo te propongo empezar con un ejemplo concreto: encuentra el dominio de "
                "f(x) = 1/(x - 4). Primero identifica qué valor hace cero el denominador "
                "y después escribe el conjunto de valores permitidos. No hay que asumir "
                "restricciones como -2 o 2 sin ver la función.")
    if re.search(r"recta|vertical|horizontal", topic):
        return ("Yo empezaría por la idea central de la prueba de la recta vertical: "
                "una gráfica representa una función si ninguna recta vertical la corta en más de un punto. "
                "Después podemos practicar con una parábola o una circunferencia.")
    return "Yo empezaría por la idea central del tema y después propondría un ejercicio corto para comprobarla."


def _response_is_relevant(question: str, answer: str, conversation_context: str = "") -> bool:
    """Cheap output guard against a model answering the wrong retrieved topic."""
    query = _student_text(question).lower()
    text = _student_text(answer).lower()
    active = _student_text(conversation_context).lower()
    if re.search(r"matriz|matrices", query) or (len(query.split()) <= 5 and re.search(r"matriz|matrices", active)):
        matrix_terms = ("matriz", "entrada", "dimensión", "dimension", "posición", "posicion", "escalar")
        unrelated = ("topografía", "ley de senos", "cosecante", "modelado con ecuaciones")
        return any(term in text for term in matrix_terms) and not any(term in text for term in unrelated)
    # Short follow-ups depend on the active problem stored in memory. They do
    # not necessarily repeat the topic word, so do not reject a coherent
    # contextual answer merely because the current turn says "¿por qué?" or
    # "dame un ejemplo".
    if re.search(r"\b(?:por qué|porque|eso|ejemplo|practicar|comprobar|verificar)\b", query):
        return not any(term in text for term in ("secante", "cosecante", "sistemas lineales"))
    unrelated_trig = ("secante", "cosecante", "cotangente", "trigonom")
    if re.search(r"factoriz|factor", query):
        return ("factor" in text or "polinom" in text or "x²" in text or "x^2" in text) and not (
            any(term in text for term in unrelated_trig) and "factor" not in text
        )
    if "dominio" in query or "denominador" in query:
        return any(term in text for term in ("dominio", "denominador", "cero", "exclu"))
    if "función" in query or "funcion" in query:
        return any(term in text for term in ("func", "relación", "relacion", "dominio", "rango"))
    if "producto punto" in query or "producto escalar" in query:
        vector_terms = ("vector", "componente", "a·b", "a · b", "cos")
        unrelated = ("interés continuo", "capital invertido", "sen(15", "identidad trigonométrica")
        return any(term in text for term in vector_terms) and not any(term in text for term in unrelated)
    return True


def _response_is_spanish(answer: str) -> bool:
    """Reject an otherwise fluent answer in the wrong language.

    Very short symbolic answers (for example ``x = 3``) are language-neutral;
    longer prose must contain Spanish function words and must not look like an
    English-only completion.
    """
    text = _student_text(answer).strip().lower()
    words = re.findall(r"[a-záéíóúñü]{2,}", text)
    if len(words) < 6:
        return bool(re.search(r"[=(){}+\-*/^√≤≥]|\d", text))
    spanish = {"el", "la", "los", "las", "que", "para", "con", "una", "un", "es", "del", "por", "como", "puedes", "buscamos", "resultado", "porque"}
    english = {"the", "this", "that", "you", "your", "with", "find", "because", "answer", "step", "we", "are", "is"}
    es_count = sum(word in spanish for word in words)
    en_count = sum(word in english for word in words)
    # A Spanish answer may contain an occasional technical English token
    # (``factor``, ``let`` in a formula, etc.). Reject only when English
    # markers clearly dominate the response.
    # Be permissive with mathematical vocabulary and proper names from the
    # textbook. Reject only clearly English-dominant prose; otherwise Qwen's
    # occasional technical token would trigger an unnecessary remote fallback.
    return not (en_count >= 4 and en_count > max(1, es_count * 3))


def _response_has_prompt_leak(answer: str) -> bool:
    """Detect internal prompt/XML/reasoning content before it reaches a user."""
    lowered = answer.lower()
    leaked = (
        "<think>", "</think>", "<student_response>", "<instructional_trace>",
        "contexto de la conversación:", "pregunta del estudiante:",
        "system message", "chain of thought", "razonamiento interno",
    )
    return any(marker in lowered for marker in leaked)


def _response_passes_guardrails(question: str, answer: str, conversation_context: str = "") -> tuple[bool, str]:
    if not answer.strip():
        return False, "respuesta vacía"
    if _response_has_prompt_leak(answer):
        return False, "posible fuga de prompt o razonamiento"
    if not _response_is_spanish(answer):
        return False, "idioma no compatible con la interfaz"
    if not _response_is_relevant(question, answer, conversation_context):
        return False, "respuesta fuera de contexto"
    if re.search(r"\b(?:dame|ponme|prop[oó]n|quiero)\s+(?:otro\s+|un\s+|una\s+)?(?:ejercicio|problema|pr[aá]ctica)\b", question, re.I):
        # An exercise request must contain an actionable statement, not only an
        # invitation to write a first step.  This catches provider responses
        # that sound pedagogical but omit the actual problem.
        has_task = bool(re.search(r"(?:=|\bcalcula\b|\bsimplifica\b|\bfactoriza\b|\bencuentra\b|\bresuelve\b|\bdetermina\b|\d\s*[+\-*/^])", answer, re.I))
        if not has_task:
            return False, "ejercicio sin enunciado accionable"
    return True, "ok"


def _needs_llm_guardrail_review(question: str, answer: str, provider: str) -> bool:
    """Limit second-pass checks to ambiguous generated turns."""
    # Never call a remote verifier from the deterministic unit-test suite.
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    if not _bool_env("AI_TUTOR_GUARDRAIL_DOUBLE_CHECK", False) or provider == "deepseek":
        return False
    return bool(
        re.search(r"\b(?:correcto|correcta|exacto|verific|comprueb|ejercicio|problema|factoriz|dominio)\b", question + " " + answer, re.I)
        or re.search(r"[=²³^/]", answer)
    )


class TutorApplicationService:
    """Application boundary shared by FastAPI and future cloud workers."""

    def __init__(self, repository=None):
        config = load_config()
        database_url = os.getenv("AI_TUTOR_DATABASE_URL", "").strip()
        database_path = database_url or project_path(config["paths"]["conversations"])
        self.repository = repository or ConversationRepository(database_path)
        self.memory = ConversationMemory(self.repository, **config.get("memory", {}))
        self.auth = AuthenticationService(self.repository)
        self.learning = LearningProfileService(self.repository)
        self.understanding = UnderstandingEvaluator()
        concepts = read_jsonl(project_path(config["paths"]["concepts"]))
        self.concept_labels = {item["concept_id"]: item.get("concept_name", item["concept_id"]) for item in concepts}
        generation_cfg = config.get("generation", {})
        self.default_provider = os.getenv("AI_TUTOR_DEFAULT_PROVIDER", generation_cfg.get("provider", "local_qwen3_1_7b"))
        configured_fallbacks = generation_cfg.get("fallback_providers", ["deepseek", "openai", "instructional"])
        env_fallbacks = os.getenv("AI_TUTOR_FALLBACK_PROVIDERS", "").strip()
        self.fallback_providers = [item.strip() for item in (env_fallbacks.split(",") if env_fallbacks else configured_fallbacks) if item.strip()]
        if "instructional" not in self.fallback_providers:
            self.fallback_providers.append("instructional")
        self.default_retrieval = os.getenv("AI_TUTOR_DEFAULT_RETRIEVAL", "pep_plan_rag")
        if os.getenv("AI_TUTOR_ENV", "development").lower() == "production" and self.default_retrieval != "pep_plan_rag":
            raise RuntimeError("La configuración de producción debe usar pep_plan_rag (PEP-Plan-RAG v3)")
        self.allow_fallback = _bool_env("AI_TUTOR_ALLOW_MODEL_FALLBACK", True)
        self._tutors: dict[str, Tutor] = {}
        self._tutor_lock = Lock()
        self.protocol_pdf = project_path("data/protocol/Proyecto_doctoral_manejo_etico_de_datos.pdf")
        self.protocol_version = self._protocol_version()
        config_paths = load_config().get("paths", {})
        self.project_paths = {name: project_path(value) for name, value in config_paths.items() if name in {"chunks", "concepts", "relations", "graph", "indexes"}}
        self._learning_path_data = None

    def learning_path(self, user_id: str):
        """Return a compact, student-facing route derived from current evidence."""
        if self._learning_path_data is None:
            relations_path = self.project_paths.get("relations")
            if not relations_path or not relations_path.exists():
                return {"items": [], "target_concepts": [], "missing_prerequisites": []}
            graph = nx.DiGraph()
            for relation in read_jsonl(relations_path):
                source = relation.get("source_id")
                target = relation.get("target_id")
                if source and target:
                    graph.add_edge(source, target, edge_type=relation.get("edge_type"),
                                   weight=relation.get("weight", 1.0),
                                   confidence=relation.get("confidence", 1.0))
            concepts = read_jsonl(project_path(load_config()["paths"]["concepts"]))
            labels = {item["concept_id"]: item.get("concept_name", item["concept_id"]) for item in concepts}
            self._learning_path_data = (graph, labels, concepts)
        graph, labels, concepts = self._learning_path_data
        state = self.learning.state_for(user_id)
        routes = build_learning_routes(concepts, state)
        targets = []
        for conversation in self.repository.list_conversations(user_id):
            messages = self.repository.list_messages(user_id, conversation.conversation_id, limit=20)
            for message in reversed(messages):
                if message.role == "assistant":
                    targets.extend(message.metadata.get("concepts", []) if message.metadata else [])
                    break
            if targets:
                break
        if not targets:
            targets = [concept_id for concept_id, mastery in state.concept_mastery.items() if mastery < 0.65]
        if not targets:
            targets = list(labels)[:1]
        path = build_learning_path(graph, list(dict.fromkeys(targets))[:5], state, labels, max_depth=3, max_nodes=18)
        items = []
        for concept_id in path["ordered_concepts"]:
            mastery = round(path["mastery"].get(concept_id, state.mastery_for(concept_id, labels.get(concept_id, ""))), 3)
            items.append({
                "concept_id": concept_id,
                "label": labels.get(concept_id, concept_id.replace("_", " ")),
                "mastery": mastery,
                "status": "completed" if mastery >= path["mastery_threshold"] else ("next" if not items else "practice"),
                "is_prerequisite": concept_id in path["missing_prerequisites"],
            })
        return {"routes": routes, "items": items, "target_concepts": path["target_concepts"],
                "missing_prerequisites": path["missing_prerequisites"],
                "mastery_threshold": path["mastery_threshold"]}

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

    def emergency_answer(self, identity: dict, conversation_id: str, message: str, reason: str = "capacity"):
        """Return a local answer when the generation queue is saturated.

        This path is deliberately deterministic and short: the student gets a
        useful response instead of an HTTP timeout while the capacity event is
        retained in turn metadata for later analysis.
        """
        started = time.perf_counter()
        prepared = self.memory.prepare(identity["user_id"], conversation_id, message)
        prompt = (
            "Pregunta del estudiante:\n" + message +
            "\nContexto de la conversación:\n" + prepared["conversation_context"] +
            "\n<evidence>\n</evidence>\nConceptos recuperados:\n\n"
            "Prerrequisitos detectados:\n\n"
        )
        generated = InstructionalGenerator().generate(prompt)
        metadata = {
            "retrieval_method": self.default_retrieval,
            "model_provider": "instructional_emergency",
            "effective_model": generated.model,
            "student_profile": f"persistent:{identity['user_id']}",
            "retrieval_query": message,
            "chunks": [], "concepts": [],
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "fallback_used": True,
            "fallback_reason": reason,
            "requested_provider": self.default_provider,
        }
        self.memory.record_turn(identity["user_id"], conversation_id, message, generated.text, metadata)
        return {"answer": generated.text, "metadata": metadata}

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
        context_decision = route_turn(
            message,
            prepared["messages"],
            prepared["conversation"].active_problem,
            prepared["conversation"].pedagogical_state,
        )
        pending_intent = context_decision.intent if context_decision.intent in {
            "exercise_request", "exercise_confirmation", "choose_for_student", "decline_activity"
        } else _pending_activity_intent(message, prepared["messages"])
        if _pending_decline(message, prepared["conversation"].pedagogical_state):
            started = time.perf_counter()
            answer = "De acuerdo, dejamos el ejercicio cerrado por ahora. Cuando quieras, podemos practicar otro parecido o repasar otro concepto."
            state = {**(prepared["conversation"].pedagogical_state or {}), "current_activity": "review", "pending_question": answer, "expected_response_type": "student_choice", "next_action": "offer_exercise"}
            metadata = {
                "intent": "decline_follow_up", "context_decision": "decline_follow_up", "retrieval_method": "none",
                "model_provider": "conversation_router", "student_profile": f"persistent:{user_id}", "retrieval_query": message,
                "chunks": [], "concepts": [], "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "effective_model": "conversation-choice-router-v1", "pedagogical_state": state,
                "fallback_used": False, "requested_provider": self.default_provider,
            }
            self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
            return {"answer": answer, "metadata": metadata}
        if pending_intent in {"exercise_request", "exercise_confirmation"}:
            started = time.perf_counter()
            answer = _exercise_for_topic(prepared["conversation"].active_problem)
            state = {
                **(prepared["conversation"].pedagogical_state or {}),
                "topic": prepared["conversation"].active_problem,
                "current_activity": "guided_exercise",
                "pending_question": answer,
                "expected_response_type": "student_attempt",
                "next_action": "check_attempt",
            }
            metadata = {
                "intent": pending_intent,
                "retrieval_method": "none",
                "model_provider": "conversation_router",
                "student_profile": f"persistent:{user_id}",
                "retrieval_query": prepared["retrieval_query"],
                "chunks": [], "concepts": [],
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "effective_model": "pedagogical-state-router-v1",
                "pedagogical_state": state,
                "fallback_used": False,
                "requested_provider": self.default_provider,
            }
            self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
            return {"answer": answer, "metadata": metadata}
        if pending_intent == "choose_for_student":
            started = time.perf_counter()
            answer = _starting_point_for_topic(prepared["conversation"].active_problem)
            state = {**(prepared["conversation"].pedagogical_state or {}),
                     "topic": prepared["conversation"].active_problem,
                     "current_activity": "topic_introduction", "expected_response_type": "student_choice",
                     "pending_question": "¿Quieres que lo veamos con un ejemplo?", "next_action": "offer_example"}
            metadata = {"intent": pending_intent, "retrieval_method": "none", "model_provider": "conversation_router",
                        "student_profile": f"persistent:{user_id}", "retrieval_query": prepared["retrieval_query"],
                        "chunks": [], "concepts": [], "latency_ms": round((time.perf_counter()-started)*1000, 2),
                        "effective_model": "pedagogical-state-router-v1", "pedagogical_state": state,
                        "fallback_used": False, "requested_provider": self.default_provider}
            self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
            return {"answer": answer, "metadata": metadata}
        if pending_intent == "decline_activity":
            started = time.perf_counter()
            answer = "Está bien. Podemos revisar la explicación primero y luego intentar un ejercicio cuando te sientas preparado."
            state = {**(prepared["conversation"].pedagogical_state or {}), "topic": prepared["conversation"].active_problem, "current_activity": "review", "next_action": "offer_exercise"}
            metadata = {"intent": pending_intent, "retrieval_method": "none", "model_provider": "conversation_router",
                        "student_profile": f"persistent:{user_id}", "retrieval_query": message, "chunks": [], "concepts": [],
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2), "effective_model": "pedagogical-state-router-v1",
                        "pedagogical_state": state, "fallback_used": False, "requested_provider": self.default_provider}
            self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
            return {"answer": answer, "metadata": metadata}
        if context_decision.intent == "decline_example":
            started = time.perf_counter()
            answer = (
                "No pasa nada. Te propongo una función para practicar: "
                "f(x) = 1/(x + 2). Para encontrar su dominio, empieza por localizar "
                "el valor de x que hace cero el denominador. ¿Cuál obtienes?"
            )
            state = {**(prepared["conversation"].pedagogical_state or {}),
                     "topic": prepared["conversation"].active_problem,
                     "current_activity": "guided_example", "pending_question": answer,
                     "expected_response_type": "conceptual_answer", "next_action": "check_attempt"}
            metadata = {"intent": "decline_example", "context_decision": "decline_example",
                        "retrieval_method": "none", "model_provider": "conversation_router",
                        "student_profile": f"persistent:{user_id}", "retrieval_query": message,
                        "chunks": [], "concepts": [], "latency_ms": round((time.perf_counter()-started)*1000, 2),
                        "effective_model": "conversation-state-router-v1", "pedagogical_state": state,
                        "fallback_used": False, "requested_provider": self.default_provider}
            self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
            return {"answer": answer, "metadata": metadata}
        is_domain_example = bool(re.search(
            r"dominio|denominador|funci[oó]n\s+racional|expresi[oó]n\s+racional",
            (prepared["conversation"].active_problem or "") + " " + context_decision.retrieval_query,
            re.I,
        ))
        if context_decision.intent == "student_example" and is_domain_example:
            # A submitted example is a response to the pending tutor prompt.
            # Resolve the small symbolic constraint locally first; this avoids
            # asking a generative model to infer which turn the expression
            # belongs to and gives the same answer across providers.
            started = time.perf_counter()
            prompt = ("Pregunta del estudiante:\nEncontrar el dominio de la función racional " + message +
                      "\nContexto de la conversación:\n" + prepared["conversation_context"] +
                      "\n<evidence>\n</evidence>\nConceptos recuperados: dominio, función racional\n"
                      "Prerrequisitos detectados:\n")
            generated = InstructionalGenerator().generate(prompt)
            answer = generated.text
            state = {**(prepared["conversation"].pedagogical_state or {}),
                     "current_activity": "guided_example", "pending_question": answer,
                     "expected_response_type": "conceptual_answer", "next_action": "continue_or_check"}
            metadata = {"intent": "student_example", "context_decision": "student_example",
                        "retrieval_method": self.default_retrieval, "model_provider": "instructional_state_guardrail",
                        "student_profile": f"persistent:{user_id}", "retrieval_query": prepared["retrieval_query"],
                        "chunks": [], "concepts": ["domain", "rational_functions"],
                        "latency_ms": round((time.perf_counter()-started)*1000, 2),
                        "effective_model": generated.model, "pedagogical_state": state,
                        "fallback_used": False, "requested_provider": self.default_provider,
                        "answer_guardrail_used": True, "answer_guardrail": "pending_example_state_v1"}
            self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
            return {"answer": answer, "metadata": metadata}
        if context_decision.intent == "feedback_check":
            started = time.perf_counter()
            evaluation = context_decision.evaluation
            if evaluation.get("status") == "incorrect" and evaluation.get("evaluator") == "feedback_check_exponents_v1":
                answer = (
                    "Tu idea de sumar los exponentes iba bien, pero el resultado escrito no era correcto: "
                    "3 + 2 = 5, no 6. Por eso 2³ · 2² = 2⁵ = 32."
                )
            elif evaluation.get("status") == "correct":
                answer = "Sí, tu respuesta es correcta. Comprobemos ahora por qué funciona la regla para que puedas aplicarla en otro ejemplo."
            else:
                answer = "Puedo comprobarlo, pero necesito volver a ver el ejercicio y tu procedimiento para no marcarlo como correcto sin evidencia."
            state = {**(prepared["conversation"].pedagogical_state or {}),
                     "topic": prepared["conversation"].active_problem,
                     "current_activity": "feedback_review",
                     "next_action": "continue_or_retry"}
            metadata = {
                "intent": "feedback_check", "context_decision": "feedback_check",
                "feedback_evaluation": evaluation, "retrieval_method": "none",
                "model_provider": "conversation_router", "student_profile": f"persistent:{user_id}",
                "retrieval_query": message, "chunks": [], "concepts": [],
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "effective_model": "feedback-evaluator-v1", "pedagogical_state": state,
                "fallback_used": False, "requested_provider": self.default_provider,
            }
            self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
            return {"answer": answer, "metadata": metadata}
        if context_decision.intent == "feedback_uncertain" or (
            context_decision.intent == "feedback_answer" and
            (context_decision.evaluation.get("reason") == "negación o duda ante la pregunta pendiente" or
             context_decision.evaluation.get("status") == "uncertain") and
            re.fullmatch(r"\s*(?:no|ahora no|no s[eé])\s*[.!?]*", message, re.I)
        ):
            started = time.perf_counter()
            topic = prepared["conversation"].active_problem or "este ejercicio"
            latest_question = next(
                (item.content for item in reversed(prepared["messages"])
                 if item.role == "assistant" and ("?" in item.content or "¿" in item.content)),
                "¿Qué parte quieres revisar?",
            )
            if "¿" in latest_question:
                latest_question = "¿" + latest_question.rsplit("¿", 1)[-1].strip()
            answer = (
                f"Parece que estás dudando, y está bien: seguimos con {topic}. "
                "No voy a cambiar de tema ni asumir una respuesta. Podemos revisar el paso anterior "
                f"juntos. La pregunta que quedó pendiente era: {latest_question}"
            )
            state = {**(prepared["conversation"].pedagogical_state or {}),
                     "topic": topic, "current_activity": "feedback_review",
                     "pending_question": latest_question, "expected_response_type": "clarification",
                     "next_action": "ask_clarifying_question", "last_step_closed": False}
            metadata = {
                "intent": "feedback_uncertain", "context_decision": "feedback_uncertain",
                "feedback_evaluation": context_decision.evaluation, "retrieval_method": "none",
                "model_provider": "conversation_router", "student_profile": f"persistent:{user_id}",
                "retrieval_query": message, "chunks": [], "concepts": [],
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "effective_model": "conversation-uncertainty-router-v1", "pedagogical_state": state,
                "fallback_used": False, "requested_provider": self.default_provider,
            }
            self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
            return {"answer": answer, "metadata": metadata}
        pending_action = _pending_action_intent(message, prepared["conversation"].pedagogical_state)
        if pending_action == "continue_verification":
            started = time.perf_counter()
            prior_state = prepared["conversation"].pedagogical_state or {}
            answer, roots, index = _verification_step(prepared["conversation"].active_problem, prior_state)
            state = {
                **prior_state,
                "current_activity": "verification",
                "pending_question": answer,
                "expected_response_type": "student_attempt",
                "next_action": "check_attempt",
                "last_step_closed": False,
                "verification_roots": roots,
                "verification_index": index,
            }
            metadata = {
                "intent": "continue_verification",
                "context_decision": "continue_verification",
                "retrieval_method": "none",
                "model_provider": "conversation_router",
                "student_profile": f"persistent:{user_id}",
                "retrieval_query": message,
                "chunks": [],
                "concepts": [],
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "effective_model": "verification-state-router-v1",
                "pedagogical_state": state,
                "fallback_used": False,
                "requested_provider": self.default_provider,
            }
            self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
            return {"answer": answer, "metadata": metadata}
        prior_state = prepared["conversation"].pedagogical_state or {}
        if prior_state.get("current_activity") == "verification" and re.fullmatch(r"\s*0(?:[.,]0+)?\s*[.!?]*", message or ""):
            started = time.perf_counter()
            roots = list(prior_state.get("verification_roots") or [])
            index = int(prior_state.get("verification_index", 0))
            next_index = index + 1
            if roots and next_index < len(roots):
                root = roots[next_index]
                answer = f"Correcto: al sustituir x = {roots[index]}, el resultado es 0. Ahora comprueba x = {root}: {root}² - 5·{root} + 6. ¿Qué obtienes?"
                state = {**prior_state, "pending_question": answer, "verification_index": next_index, "next_action": "check_attempt"}
            else:
                answer = "Correcto: ambas sustituciones dan 0, así que las dos raíces quedan verificadas. ¿Quieres practicar otro ejercicio o prefieres repasar otro concepto?"
                state = {**prior_state, "current_activity": "review", "pending_question": answer, "expected_response_type": "student_choice", "next_action": "offer_exercise", "last_step_closed": True}
            metadata = {
                "intent": "verification_answer", "context_decision": "verification_answer",
                "retrieval_method": "none", "model_provider": "conversation_router",
                "student_profile": f"persistent:{user_id}", "retrieval_query": message,
                "chunks": [], "concepts": [], "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "effective_model": "verification-check-v1", "pedagogical_state": state,
                "fallback_used": False, "requested_provider": self.default_provider,
            }
            self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
            return {"answer": answer, "metadata": metadata}
        if _is_progress_confirmation(message, prepared["conversation"].pedagogical_state):
            # Close the pending micro-step instead of sending the same question
            # back to the generator.  The next turn starts from an explicit
            # choice, so ``siguiente`` and ``verificados`` cannot create a loop.
            started = time.perf_counter()
            answer = (
                "Perfecto, dejamos ese paso verificado. "
                "¿Quieres practicar un ejercicio parecido o prefieres repasar otro concepto?"
            )
            state = {
                **(prepared["conversation"].pedagogical_state or {}),
                "current_activity": "review",
                "pending_question": answer,
                "expected_response_type": "student_choice",
                "next_action": "offer_exercise",
                "last_step_closed": True,
            }
            metadata = {
                "intent": "progress_confirmation",
                "context_decision": "progress_confirmation",
                "retrieval_method": "none",
                "model_provider": "conversation_router",
                "student_profile": f"persistent:{user_id}",
                "retrieval_query": message,
                "chunks": [],
                "concepts": [],
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "effective_model": "progress-state-router-v1",
                "pedagogical_state": state,
                "fallback_used": False,
                "requested_provider": self.default_provider,
            }
            self.memory.record_turn(user_id, conversation_id, message, answer, metadata)
            return {"answer": answer, "metadata": metadata}
        social_intent = _social_intent(message)
        if social_intent:
            started = time.perf_counter()
            first_name = identity.get("display_name", "").strip().split(" ")[0] or "estudiante"
            answers = {
                "greeting": f"¡Hola, {first_name}! Soy PATI. ¿Qué tema o ejercicio de Precálculo quieres trabajar hoy?",
                "thanks": "¡Con gusto! Antes de seguir, ¿sientes que la idea quedó clara o quieres comprobarla con un ejemplo corto?",
                "goodbye": "¡Hasta luego! Cuando regreses podemos continuar desde esta misma conversación.",
                "acknowledgement": "Perfecto, sigamos desde ahí. ¿Quieres continuar con el siguiente paso o prefieres comprobar lo que acabamos de hacer?",
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

        if _open_question(message):
            started = time.perf_counter()
            first_name = identity.get("display_name", "").strip().split(" ")[0] or "estudiante"
            answer = (
                f"Puedo ayudarte con Precálculo, {first_name}. "
                "Podemos trabajar álgebra, funciones, ecuaciones, trigonometría, "
                "dominio, gráficas o cualquier ejercicio paso a paso. "
                "¿Qué tema o problema quieres revisar?"
            )
            metadata = {
                "intent": "open_question",
                "retrieval_method": "none",
                "model_provider": "conversation_router",
                "student_profile": f"persistent:{user_id}",
                "retrieval_query": message,
                "chunks": [],
                "concepts": [],
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "effective_model": "deterministic-conversation-router-v1",
                "fallback_used": False,
                "requested_provider": self.default_provider,
            }
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
        if context_decision.evaluation:
            evaluation = context_decision.evaluation
            conversation_context += (
                "\n\nEvaluación del turno por el controlador conversacional: "
                f"estado={evaluation.get('status', 'uncertain')}; "
                f"confianza={evaluation.get('confidence', 0.0):.2f}; "
                f"razón={evaluation.get('reason', 'no disponible')}. "
                "No afirmes que la respuesta es correcta si el estado es uncertain."
            )
        if verification:
            verdict = "CORRECTA" if verification["status"] == "correct" else "INCORRECTA"
            expected = verification.get("expected_value", verification.get("expected_symbol", ""))
            conversation_context += (
                "\n\nVerificación matemática determinista del turno actual: "
                f"la respuesta {message!r} es {verdict}. "
                f"Valor o símbolo esperado: {expected}. "
                f"Regla: {verification['explanation']}. "
                "Respeta esta verificación; reconoce una respuesta correcta y continúa el ejercicio. "
                "No reinicies la conversación como un saludo. No felicites una respuesta incorrecta."
            )
        elif previous_tutor and "?" in previous_tutor.content and len(message.strip()) <= 40:
            conversation_context += (
                "\n\nLa respuesta breve actual no tiene verificación automática disponible. "
                "No afirmes que es correcta sin comprobarla explícitamente dentro de tu respuesta."
            )
        provider = self.default_provider
        retrieval_method = self.default_retrieval
        response = None
        last_response = None
        requested_error = ""
        primary_provider_error = ""
        model_fallback_used = False
        effective_provider = provider
        double_check_status = "not_requested"
        double_check_reason = ""
        providers = [provider] + ([item for item in self.fallback_providers if item != provider] if self.allow_fallback else [])
        provider_errors = []
        for candidate in providers:
            try:
                candidate_response = self.tutor(candidate).ask(
                    message,
                    retrieval_method,
                    knowledge_mode="instructional_database",
                    student_profile=profile,
                    conversation_context=conversation_context,
                    retrieval_query=prepared["retrieval_query"],
                    pedagogical_state=prepared["conversation"].pedagogical_state,
                    intent=pending_intent or "",
                )
                last_response = candidate_response
                if candidate_response.generation_error or not candidate_response.answer.strip():
                    failure = candidate_response.generation_error or "respuesta vacía"
                    provider_errors.append(f"{candidate}: {failure}")
                    requested_error = "; ".join(provider_errors)
                    primary_provider_error = candidate_response.primary_generation_error
                    continue
                valid, guardrail_reason = _response_passes_guardrails(message, candidate_response.answer, conversation_context)
                if not valid:
                    provider_errors.append(f"{candidate}: {guardrail_reason}")
                    requested_error = "; ".join(provider_errors)
                    continue
                if _needs_llm_guardrail_review(message, candidate_response.answer, candidate):
                    review = review_with_deepseek(message, candidate_response.answer, conversation_context)
                    double_check_status = review.status
                    double_check_reason = review.reason
                    if review.status == "rejected":
                        provider_errors.append(f"{candidate}: doble check DeepSeek rechazó la respuesta ({review.reason})")
                        requested_error = "; ".join(provider_errors)
                        continue
                response = candidate_response
                effective_provider = candidate
                requested_error = "; ".join(provider_errors)
                model_fallback_used = candidate != provider or candidate_response.model_fallback_used
                break
            except Exception as exc:  # provider initialization/network error
                provider_errors.append(f"{candidate}: {exc}")
                requested_error = "; ".join(provider_errors)
        if response is None:
            # The student must not receive a provider/HTTP error.  Use the
            # deterministic instructional generator as a final local answer,
            # even when a provider was initialized but its output failed a
            # guardrail.  The technical reason remains in metadata/logs for
            # research diagnostics.
            emergency_prompt = (
                "Pregunta del estudiante:\n" + message +
                "\nContexto de la conversación:\n" + conversation_context +
                "\n<evidence>\n</evidence>\nConceptos recuperados:\n\n"
                "Prerrequisitos detectados:\n\n"
            )
            emergency = InstructionalGenerator().generate(emergency_prompt)
            if last_response is not None:
                response = last_response
                response.answer = emergency.text
                response.generation_provider = "instructional_emergency"
                response.generation_model = emergency.model
                response.generation_error = requested_error or "provider unavailable"
            else:
                response = TutorResponse(
                    answer=emergency.text,
                    retrieval=RetrievalResult(message, [], [], [], {"method": retrieval_method}, 0.0, {}),
                    generation_latency_ms=emergency.latency_ms,
                    total_latency_ms=emergency.latency_ms,
                    generation_provider="instructional_emergency",
                    generation_model=emergency.model,
                    generation_error=requested_error or "provider unavailable",
                    model_fallback_used=True,
                    primary_generation_error=primary_provider_error,
                )
            effective_provider = "instructional_emergency"
            model_fallback_used = True

        concepts = list(response.retrieval.concepts)
        answer = _student_text(response.answer)
        pedagogical_state = dict(prepared["conversation"].pedagogical_state or {})
        pedagogical_state.setdefault("topic", prepared["conversation"].active_problem)
        # Persist the shape of the next expected learner turn.  This is a
        # lightweight state/intent model (not an LLM guess) and lets the next
        # message such as ``no`` or ``1/(x+2)`` be interpreted against the
        # tutor's actual question instead of being sent as a fresh retrieval.
        if re.search(r"(?:ejemplo\s+(?:espec[ií]fico|concreto)|funci[oó]n\s+concreta|expresi[oó]n\s+concreta|enunciado\s+(?:concreto|completo))", answer, re.I):
            pedagogical_state.update({"pending_question": answer[-600:], "expected_response_type": "example_submission",
                                      "current_activity": "concept_explanation", "next_action": "await_example"})
        elif re.search(r"(?:quieres|prefieres|te gustar[ií]a).{0,100}\?", answer, re.I):
            pedagogical_state.update({"pending_question": answer[-600:], "expected_response_type": "student_choice",
                                      "next_action": "await_choice"})
        elif "?" in answer or "¿" in answer:
            pedagogical_state.update({"pending_question": answer[-600:], "expected_response_type": "conceptual_answer",
                                      "next_action": "check_answer"})
        if re.search(r"\b(?:repasar|revisar|recordar)\b", message, re.IGNORECASE):
            pedagogical_state.update({"current_activity": "topic_introduction", "expected_response_type": "activity_choice",
                                      "pending_question": "¿Quieres empezar por la explicación o prefieres trabajar un ejercicio?",
                                      "next_action": "wait_for_activity_choice"})
        metadata = {
            "intent": pending_intent or context_decision.intent,
            "context_decision": context_decision.intent,
            "context_follow_up": context_decision.is_follow_up,
            "feedback_evaluation": context_decision.evaluation,
            "retrieval_method": retrieval_method,
            "model_provider": effective_provider,
            "student_profile": profile.profile_id,
            "retrieval_query": prepared["retrieval_query"],
            "chunks": [chunk.chunk_id for chunk in response.retrieval.chunks],
            "concepts": concepts,
            "retrieval_debug": {
                "query": response.retrieval.query,
                "scores": [round(float(score), 5) for score in response.retrieval.scores],
                "final_chunks": response.retrieval.debug_info.get("final_chunks", []),
                "context_buckets": response.retrieval.debug_info.get("context_buckets", {}),
            },
            "latency_ms": round(response.total_latency_ms, 2),
            "effective_model": response.generation_model,
            "fallback_used": effective_provider != provider or model_fallback_used,
            "requested_provider": provider,
            "requested_provider_error": requested_error or primary_provider_error,
            "guardrail_double_check": {
                "status": double_check_status,
                "reason": double_check_reason,
                "provider": "deepseek",
            },
            "response_verification": verification or {"status": "not_available"},
            "pedagogical_state": pedagogical_state,
        }
        # Mathematical guardrail for the common monic quadratic exercise. A
        # small local model can produce fluent but invalid factor pairs; use
        # the deterministic symbolic checker as the authority for the final
        # equality while retaining the configured model for pedagogy.
        deterministic_factorization = InstructionalGenerator._factor_quadratic(message)
        if deterministic_factorization:
            answer = deterministic_factorization
            metadata["answer_guardrail_used"] = True
            metadata["answer_guardrail"] = "quadratic_factorization_v1"
        if verification and verification["status"] == "incorrect" and verification.get("kind") == "numeric_linear_denominator_v1":
            student_value = verification["student_value"]
            expected_value = verification["expected_value"]
            answer = (
                f"Revisemos esa respuesta: si sustituyes x = {student_value:g}, "
                "el denominador no queda en cero. Para encontrar el valor que debemos excluir, "
                f"resolvemos {verification['explanation']}. Por eso el valor correcto es "
                f"x = {expected_value:g}, no {student_value:g}. "
                "¿Puedes comprobarlo sustituyendo ese valor en el denominador?"
            )
        elif verification and verification["status"] == "incorrect" and verification.get("kind") == "symbolic_common_factor_v1":
            answer = (
                f"Casi: la letra que se repite en ambos términos es {verification['expected_symbol']}. "
                f"En la expresión mencionada, {verification['expected_symbol']}² + 3{verification['expected_symbol']}, "
                f"el factor común es {verification['expected_symbol']}. ¿Puedes identificar ahora qué queda dentro del paréntesis?"
            )
        elif verification and verification["status"] == "correct" and verification.get("kind") == "symbolic_common_factor_v1":
            answer = (
                f"Sí, correcto: {verification['expected_symbol']} es el factor común porque aparece en los dos términos. "
                f"Al extraerlo, la expresión queda {verification['expected_symbol']}({verification['expected_symbol']} + 3). "
                "¿Qué observas dentro del paréntesis?"
            )
            metadata["answer_guardrail_used"] = True
        elif verification and verification.get("kind") == "numeric_addition_v1":
            expected = verification["expected_value"]
            if verification["status"] == "correct":
                answer = (
                    f"Sí, correcto: sumamos las dos entradas que ocupan esa posición, y {expected:g} "
                    "es el valor de la esquina superior izquierda del resultado. "
                    "La misma regla se aplica a cada posición de las matrices."
                )
            else:
                answer = (
                    f"Revisemos la suma de esa posición: debemos combinar los dos valores correspondientes, "
                    f"y el resultado es {expected:g}. ¿Quieres que calculemos ahora la siguiente entrada?"
                )
            metadata["answer_guardrail_used"] = True
        elif verification and verification.get("kind") == "binary_function_rule_v1":
            if verification["status"] == "correct":
                answer = (
                    "Exacto: la respuesta es no. Si una misma entrada produce dos salidas distintas, "
                    "la relación no cumple la definición de función. La regla es: cada entrada debe tener "
                    "una sola salida."
                )
            else:
                answer = (
                    "En este caso, la respuesta correcta es no: una entrada con dos salidas distintas "
                    "no representa una función. ¿Quieres que lo comprobemos con un conjunto de pares ordenados?"
                )
            metadata["answer_guardrail_used"] = True
        elif verification and verification.get("kind") == "quadratic_factor_pair_v1":
            expected = verification["expected_pair"]
            if verification["status"] == "correct":
                answer = (
                    f"Sí: {expected[0]} y {expected[1]} cumplen las dos condiciones. "
                    f"Su suma es {sum(expected)} y su producto es {expected[0] * expected[1]}, "
                    "por eso son los números que necesitamos para factorizar."
                )
            else:
                answer = (
                    f"Todavía no. Para este polinomio necesitamos dos números que sumen "
                    f"{sum(expected)} y cuyo producto sea {expected[0] * expected[1]}. "
                    f"El par correcto es {expected[0]} y {expected[1]}; comprueba ambas operaciones "
                    "antes de escribir los factores."
                )
            metadata["answer_guardrail_used"] = True
        else:
            metadata.setdefault("answer_guardrail_used", False)
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
