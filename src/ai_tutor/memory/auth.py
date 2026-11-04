from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone


class AuthenticationService:
    """Local authentication suitable for a research prototype.

    PINs are never stored: SQLite contains a random salt and a PBKDF2-HMAC hash.
    Only a SHA-256 hash of the session token is persisted. This allows a
    restart or a second API instance to validate sessions without storing a
    bearer token in SQLite.
    """

    def __init__(self, repository, admin_ids=None, researcher_ids=None):
        self.repository = repository
        # `researcher_ids` remains as a backwards-compatible constructor alias;
        # persisted and issued roles are now explicitly `admin` or `student`.
        configured = admin_ids if admin_ids is not None else researcher_ids
        if configured is None:
            configured = os.getenv("AI_TUTOR_ADMIN_IDS", os.getenv("AI_TUTOR_RESEARCHER_IDS", ""))
        self.admin_ids = {repository.normalize_user_id(item) for item in configured.split(",") if item.strip()}
        self.session_ttl_seconds = max(900, min(int(os.getenv("AI_TUTOR_SESSION_TTL_SECONDS", "86400")), 604800))

    @staticmethod
    def _hash(pin: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 310_000).hex()

    @staticmethod
    def _validate_pin(pin: str):
        if len(pin or "") < 4:
            raise ValueError("El PIN debe tener al menos 4 caracteres")

    def register(self, user_id: str, display_name: str, pin: str):
        self._validate_pin(pin)
        user_id = self.repository.normalize_user_id(user_id)
        salt = secrets.token_bytes(16)
        role = "admin" if user_id in self.admin_ids else "student"
        user = self.repository.set_credentials(
            user_id, display_name, self._hash(pin, salt), salt.hex(), role
        )
        return self._new_session(user)

    def login(self, user_id: str, pin: str):
        user = self.repository.get_user(user_id)
        if not user or not user.get("password_hash"):
            raise ValueError("Usuario no registrado")
        candidate = self._hash(pin, bytes.fromhex(user["password_salt"]))
        if not hmac.compare_digest(candidate, user["password_hash"]):
            raise ValueError("PIN incorrecto")
        return self._new_session(user)

    def _new_session(self, user):
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=self.session_ttl_seconds)).isoformat()
        self.repository.create_session(user["user_id"], token, expires_at, now.isoformat())
        session = {"token": token, "user_id": user["user_id"], "display_name": user["display_name"],
                   "role": user["role"], "authenticated": True, "expires_at": expires_at}
        return dict(session)

    def require(self, session, role=None):
        token = (session or {}).get("token", "")
        valid = self.repository.get_session(token)
        if not valid:
            raise PermissionError("Inicia sesión para continuar")
        if role and valid["role"] != role:
            raise PermissionError("Esta operación requiere rol de administrador")
        return {"token": token, "user_id": valid["user_id"], "display_name": valid["display_name"],
                "role": valid["role"], "authenticated": True, "expires_at": valid["expires_at"]}

    def logout(self, session):
        self.repository.revoke_session((session or {}).get("token", ""))
        return {}
