from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException, Request


def _token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar")
    return authorization.split(" ", 1)[1].strip()


def current_user(request: Request, authorization: Optional[str] = Header(default=None)):
    try:
        return request.app.state.service.session(_token(authorization))
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def researcher(request: Request, authorization: Optional[str] = Header(default=None)):
    try:
        return request.app.state.service.session(_token(authorization), "researcher")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
