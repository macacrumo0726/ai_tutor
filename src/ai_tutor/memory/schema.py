from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Message:
    message_id: str
    conversation_id: str
    role: str
    content: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    conversation_id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str
    summary: str = ""
    active_problem: str = ""
    retrieval_method: str = "rag"
    model_provider: str = "instructional"
    student_profile: str = "unknown"
    archived: bool = False
    messages: Optional[list[Message]] = None
