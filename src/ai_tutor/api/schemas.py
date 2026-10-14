from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    user_id: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=1, max_length=100)
    pin: str = Field(min_length=4, max_length=128)


class LoginRequest(BaseModel):
    user_id: str
    pin: str


class SessionResponse(BaseModel):
    token: str
    user_id: str
    display_name: str
    role: str
    authenticated: bool = True


class AvatarPayload(BaseModel):
    style: str = "orbit"
    skin_tone: str = "sunny"
    hair: str = "waves"
    accessory: str = "stars"
    background: str = "violet"


class ConversationCreate(BaseModel):
    title: str = "Nueva conversación"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class FeedbackRequest(BaseModel):
    signal: Literal["understood", "partial", "needs_help"]
    concept_ids: list[str] = Field(default_factory=list)


class AdminExperimentSettings(BaseModel):
    provider: Optional[str] = None
    retrieval_method: Optional[str] = None
    allow_fallback: Optional[bool] = None


class ApiEnvelope(BaseModel):
    data: Any
