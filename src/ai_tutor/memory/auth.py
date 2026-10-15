from __future__ import annotations

import hashlib
import hmac
import os
import secrets


class AuthenticationService:
    """Local authentication suitable for a research prototype.

    PINs are never stored: SQLite contains a random salt and a PBKDF2-HMAC hash.
    Sessions live only in the running application process.
    """

    def __init__(self, repository, admin_ids=None, researcher_ids=None):
        self.repository = repository
        # `researcher_ids` remains as a backwards-compatible constructor alias;
        # persisted and issued roles are now explicitly `admin` or `student`.
        configured = admin_ids if admin_ids is not None else researcher_ids
        if configured is None:
            configured = os.getenv("AI_TUTOR_ADMIN_IDS", os.getenv("AI_TUTOR_RESEARCHER_IDS", ""))
        self.admin_ids = {repository.normalize_user_id(item) for item in configured.split(",") if item.strip()}
        self._sessions: dict[str, dict] = {}

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
        session = {"token": token, "user_id": user["user_id"], "display_name": user["display_name"],
                   "role": user["role"], "authenticated": True}
        self._sessions[token] = session
        return dict(session)

    def require(self, session, role=None):
        token = (session or {}).get("token", "")
        valid = self._sessions.get(token)
        if not valid:
            raise PermissionError("Inicia sesión para continuar")
        if role and valid["role"] != role:
            raise PermissionError("Esta operación requiere rol de administrador")
        return dict(valid)

    def logout(self, session):
        self._sessions.pop((session or {}).get("token", ""), None)
        return {}
