from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from threading import Lock
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from .dependencies import admin, current_user, protocol_user
from .schemas import AvatarPayload, ChatRequest, ConversationCreate, FeedbackRequest, LoginRequest, ProtocolAcceptanceRequest, RegisterRequest
from .services import TutorApplicationService

logger = logging.getLogger("ai_tutor.api")


class _WindowLimiter:
    """Small per-process abuse guard for auth endpoints.

    Azure can add a distributed gateway limit later; this local guard still
    prevents accidental login/register floods on a single replica.
    """
    def __init__(self, limit: int = 20, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._entries: dict[str, list[float]] = {}
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            values = [item for item in self._entries.get(key, []) if now - item < self.window_seconds]
            if len(values) >= self.limit:
                self._entries[key] = values
                return False
            values.append(now)
            self._entries[key] = values
            if len(self._entries) > 5000:
                self._entries = {name: items for name, items in self._entries.items() if items}
            return True


def _event(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def create_app(service: Optional[TutorApplicationService] = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield

    app = FastAPI(
        title="Tutor inteligente de Precálculo",
        version="0.2.0",
        description="API para la experiencia estudiantil y la investigación del tutor.",
        lifespan=lifespan,
        docs_url=None if os.getenv("AI_TUTOR_ENV", "development").lower() == "production" else "/docs",
        redoc_url=None if os.getenv("AI_TUTOR_ENV", "development").lower() == "production" else "/redoc",
    )
    # Set the dependency eagerly so the app also works with TestClient usages
    # that do not enter its context manager. The same instance is then kept
    # throughout the ASGI lifespan.
    app.state.service = service or TutorApplicationService()
    app.state.auth_limiter = _WindowLimiter(limit=int(os.getenv("AI_TUTOR_AUTH_RATE_LIMIT", "20")))
    # Ollama and free remote tiers degrade sharply under concurrent requests.
    # Queue generation instead of returning an overload error to students.
    app.state.generation_semaphore = asyncio.Semaphore(
        max(1, int(os.getenv("AI_TUTOR_MAX_CONCURRENT_GENERATIONS", "2")))
    )
    origins = [item.strip() for item in os.getenv("AI_TUTOR_CORS_ORIGINS", "http://localhost:3000").split(",") if item.strip()]
    if not origins or "*" in origins:
        raise RuntimeError("AI_TUTOR_CORS_ORIGINS debe contener orígenes explícitos; no se permite '*'")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if os.getenv("AI_TUTOR_ENV", "development").lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "precalculus-tutor-api"}

    @app.get("/api/ready")
    def ready(request: Request):
        service = request.app.state.service
        required = {
            "protocol_pdf": service.protocol_pdf,
            "chunks": service.project_paths["chunks"],
            "concepts": service.project_paths["concepts"],
            "graph": service.project_paths["graph"],
            "indexes": service.project_paths["indexes"],
        }
        missing = [name for name, path in required.items() if not path.exists()]
        if missing:
            raise HTTPException(status_code=503, detail={"status": "not_ready", "missing": missing})
        return {"status": "ready", "retrieval": service.default_retrieval, "pep_version": "v3"}

    @app.get("/api/protocol")
    def protocol(request: Request):
        return request.app.state.service.protocol_summary()

    @app.get("/api/protocol/document")
    def protocol_document(request: Request):
        path = request.app.state.service.protocol_pdf
        if not path.exists():
            raise HTTPException(status_code=503, detail="El protocolo PDF no está disponible")
        return FileResponse(path, media_type="application/pdf", filename=path.name)

    @app.post("/api/auth/register")
    def register(payload: RegisterRequest, request: Request):
        if not request.app.state.auth_limiter.allow(f"register:{request.client.host if request.client else 'unknown'}"):
            raise HTTPException(status_code=429, detail="Demasiados intentos. Espera un momento y vuelve a intentarlo.")
        try:
            return request.app.state.service.auth.register(payload.user_id, payload.display_name, payload.pin)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/auth/login")
    def login(payload: LoginRequest, request: Request):
        if not request.app.state.auth_limiter.allow(f"login:{request.client.host if request.client else 'unknown'}"):
            raise HTTPException(status_code=429, detail="Demasiados intentos. Espera un momento y vuelve a intentarlo.")
        try:
            return request.app.state.service.auth.login(payload.user_id, payload.pin)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @app.post("/api/auth/logout")
    def logout(request: Request, authorization: Optional[str] = Header(default=None), identity=Depends(current_user)):
        request.app.state.service.auth.logout({"token": (authorization or "").split(" ", 1)[-1]})
        return {"ok": True}

    @app.get("/api/me")
    def me(request: Request, identity=Depends(current_user)):
        repository = request.app.state.service.repository
        service = request.app.state.service
        return {**identity, "avatar": repository.get_avatar(identity["user_id"]), "protocol": service.protocol_status(identity["user_id"])}

    @app.get("/api/me/protocol")
    def my_protocol(request: Request, identity=Depends(current_user)):
        return request.app.state.service.protocol_status(identity["user_id"])

    @app.post("/api/me/protocol/accept")
    def accept_protocol(payload: ProtocolAcceptanceRequest, request: Request, identity=Depends(current_user)):
        try:
            acceptance = request.app.state.service.accept_protocol(
                identity["user_id"], payload.protocol_version, payload.accepted,
            )
            return {"accepted": True, "acceptance": acceptance,
                    **request.app.state.service.protocol_status(identity["user_id"])}
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/me/avatar")
    def avatar(request: Request, identity=Depends(protocol_user)):
        return request.app.state.service.repository.get_avatar(identity["user_id"])

    @app.put("/api/me/avatar")
    def update_avatar(payload: AvatarPayload, request: Request, identity=Depends(protocol_user)):
        return request.app.state.service.repository.upsert_avatar(identity["user_id"], **payload.model_dump())

    @app.get("/api/me/progress")
    def progress(request: Request, identity=Depends(protocol_user)):
        return request.app.state.service.repository.learning_report(identity["user_id"])

    @app.get("/api/me/learning-path")
    def learning_path(request: Request, identity=Depends(protocol_user)):
        return request.app.state.service.learning_path(identity["user_id"])

    @app.get("/api/conversations")
    def conversations(request: Request, identity=Depends(protocol_user)):
        service = request.app.state.service
        return [service.conversation_payload(item) for item in service.repository.list_conversations(identity["user_id"])]

    @app.post("/api/conversations")
    def create_conversation(payload: ConversationCreate, request: Request, identity=Depends(protocol_user)):
        service = request.app.state.service
        conversation = service.memory.create(
            identity["user_id"],
            title=payload.title,
            retrieval_method=service.default_retrieval,
            model_provider=service.default_provider,
            student_profile="persistent",
        )
        return service.conversation_payload(conversation)

    @app.get("/api/conversations/{conversation_id}")
    def conversation(conversation_id: str, request: Request, identity=Depends(protocol_user)):
        service = request.app.state.service
        try:
            item = service.repository.get_conversation(identity["user_id"], conversation_id, with_messages=True)
            return service.conversation_payload(item, include_messages=True)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Conversación no encontrada") from exc

    @app.delete("/api/conversations/{conversation_id}")
    def archive_conversation(conversation_id: str, request: Request, identity=Depends(protocol_user)):
        try:
            request.app.state.service.repository.archive_conversation(identity["user_id"], conversation_id)
            return {"ok": True}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Conversación no encontrada") from exc

    @app.post("/api/conversations/{conversation_id}/feedback")
    def feedback(conversation_id: str, payload: FeedbackRequest, request: Request, identity=Depends(protocol_user)):
        try:
            return request.app.state.service.feedback(identity, conversation_id, payload.concept_ids, payload.signal)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/conversations/{conversation_id}/messages/stream")
    async def chat_stream(conversation_id: str, payload: ChatRequest, request: Request, identity=Depends(protocol_user)):
        service = request.app.state.service
        try:
            service.repository.get_conversation(identity["user_id"], conversation_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Conversación no encontrada") from exc

        async def generate():
            yield _event("status", {"stage": "thinking", "message": "Estoy preparando una explicación para ti…"})
            try:
                acquired = False
                try:
                    await asyncio.wait_for(
                        request.app.state.generation_semaphore.acquire(),
                        timeout=float(os.getenv("AI_TUTOR_QUEUE_TIMEOUT_SECONDS", "12")),
                    )
                    acquired = True
                    result = await asyncio.to_thread(service.ask, identity, conversation_id, payload.message)
                except asyncio.TimeoutError:
                    # Do not leave the browser waiting behind a saturated
                    # local model. The emergency answer is persisted and is
                    # indistinguishable from a normal assistant turn.
                    result = await asyncio.to_thread(
                        service.emergency_answer, identity, conversation_id, payload.message, "generation_queue_saturated"
                    )
                finally:
                    if acquired:
                        request.app.state.generation_semaphore.release()
                words = result["answer"].split(" ")
                for index in range(0, len(words), 5):
                    yield _event("token", {"text": " ".join(words[index:index + 5]) + " "})
                    await asyncio.sleep(0.015)
                yield _event("done", result["metadata"])
            except Exception as exc:
                logger.exception("chat_stream_failed", extra={"conversation_id": conversation_id})
                yield _event("error", {"message": "No fue posible completar la respuesta. Intenta de nuevo."})

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/admin/overview")
    def admin_overview(request: Request, user_id: Optional[str] = None,
                       model_provider: Optional[str] = None,
                       retrieval_method: Optional[str] = None,
                       identity=Depends(admin)):
        service = request.app.state.service
        users = service.repository.list_study_users()
        if user_id:
            users = [item for item in users if item["user_id"] == service.repository.normalize_user_id(user_id)]
        conversation_records = []
        for user in users:
            for conversation in service.repository.list_conversations(user["user_id"], include_archived=True):
                providers = {conversation.model_provider} if conversation.model_provider else set()
                retrievals = {conversation.retrieval_method} if conversation.retrieval_method else set()
                # A fallback can change provider within one conversation. Read
                # message metadata so the dashboard reflects every model that
                # actually answered the participant, not only the last one.
                for message in service.repository.list_messages(user["user_id"], conversation.conversation_id):
                    if message.metadata.get("model_provider"):
                        providers.add(message.metadata["model_provider"])
                    if message.metadata.get("retrieval_method"):
                        retrievals.add(message.metadata["retrieval_method"])
                conversation_records.append((conversation, providers, retrievals))
        if model_provider:
            conversation_records = [item for item in conversation_records if model_provider in item[1]]
        if retrieval_method:
            conversation_records = [item for item in conversation_records if retrieval_method in item[2]]
        providers = sorted({provider for _, values, _ in conversation_records
                            for provider in values
                            if provider and provider not in {"none", "conversation_router"}})
        retrievals = sorted({method for _, _, values in conversation_records
                             for method in values
                             if method and method != "none"})
        return {
            "users": len(users),
            "provider": " · ".join(providers) if providers else service.default_provider,
            "retrieval_method": " · ".join(retrievals) if retrievals else service.default_retrieval,
            "providers": providers,
            "retrieval_methods": retrievals,
            "pep_version": "v3" if any(item == "pep_plan_rag" for item in retrievals) or (not retrievals and service.default_retrieval == "pep_plan_rag") else "not_v3",
            "fallback_enabled": service.allow_fallback,
            "filters": {"user_id": user_id, "model_provider": model_provider, "retrieval_method": retrieval_method},
        }

    @app.get("/api/admin/users")
    def admin_users(request: Request, identity=Depends(admin)):
        return request.app.state.service.repository.list_study_users()

    @app.get("/api/admin/users/{user_id}")
    def admin_user(user_id: str, request: Request, identity=Depends(admin)):
        service = request.app.state.service
        user = service.repository.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        study_ids = {item["user_id"] for item in service.repository.list_study_users()}
        if user["user_id"] not in study_ids:
            raise HTTPException(status_code=404, detail="Perfil de participante no encontrado")
        conversations = service.repository.list_conversations(user_id, include_archived=True)
        return {
            "user": {key: value for key, value in user.items() if key not in {"password_hash", "password_salt"}},
            "avatar": service.repository.get_avatar(user_id),
            "protocol": service.protocol_status(user_id),
            "profile": service.repository.learning_report(user_id),
            "conversations": [
                service.conversation_payload(
                    service.repository.get_conversation(user_id, item.conversation_id, with_messages=True),
                    include_messages=True,
                )
                for item in conversations
            ],
        }

    return app


app = create_app()
