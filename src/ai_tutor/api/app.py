from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from .dependencies import admin, current_user, protocol_user
from .schemas import AvatarPayload, ChatRequest, ConversationCreate, FeedbackRequest, LoginRequest, ProtocolAcceptanceRequest, RegisterRequest
from .services import TutorApplicationService


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
    )
    # Set the dependency eagerly so the app also works with TestClient usages
    # that do not enter its context manager. The same instance is then kept
    # throughout the ASGI lifespan.
    app.state.service = service or TutorApplicationService()
    origins = [item.strip() for item in os.getenv("AI_TUTOR_CORS_ORIGINS", "http://localhost:3000").split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "precalculus-tutor-api"}

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
        try:
            return request.app.state.service.auth.register(payload.user_id, payload.display_name, payload.pin)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/auth/login")
    def login(payload: LoginRequest, request: Request):
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
                result = await asyncio.to_thread(service.ask, identity, conversation_id, payload.message)
                words = result["answer"].split(" ")
                for index in range(0, len(words), 5):
                    yield _event("token", {"text": " ".join(words[index:index + 5]) + " "})
                    await asyncio.sleep(0.015)
                yield _event("done", result["metadata"])
            except Exception as exc:
                yield _event("error", {"message": str(exc)})

        return StreamingResponse(generate(), media_type="text/event-stream")

    @app.get("/api/admin/overview")
    def admin_overview(request: Request, identity=Depends(admin)):
        service = request.app.state.service
        users = service.repository.list_users()
        return {
            "users": len(users),
            "provider": service.default_provider,
            "retrieval_method": service.default_retrieval,
            "fallback_enabled": service.allow_fallback,
        }

    @app.get("/api/admin/users")
    def admin_users(request: Request, identity=Depends(admin)):
        return request.app.state.service.repository.list_users()

    @app.get("/api/admin/users/{user_id}")
    def admin_user(user_id: str, request: Request, identity=Depends(admin)):
        service = request.app.state.service
        user = service.repository.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
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
