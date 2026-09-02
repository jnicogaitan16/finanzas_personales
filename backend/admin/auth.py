from __future__ import annotations

import secrets
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from secrets import compare_digest
from typing import Any

import pyotp
from fastapi import HTTPException, Request, status

from config import settings

COOKIE_NAME = "finanzas_session"
_MAX_SESSIONS = 20

_sessions: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def login(username: str, password: str, totp_code: str | None = None) -> str | None:
    if not settings.admin_password:
        return None
    if not (
        compare_digest(username, settings.admin_user)
        and compare_digest(password, settings.admin_password)
    ):
        return None
    if settings.admin_totp_secret:
        if not totp_code:
            return None
        totp = pyotp.TOTP(settings.admin_totp_secret)
        if not totp.verify(totp_code.strip(), valid_window=1):
            return None
    token = secrets.token_urlsafe(32)
    _sessions[token] = {"username": username, "created": _now()}
    if len(_sessions) > _MAX_SESSIONS:
        _sessions.popitem(last=False)
    return token


def get_session(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    session = _sessions.get(token)
    if session is None:
        return None
    max_age = timedelta(hours=settings.admin_session_hours)
    if _now() - session["created"] > max_age:
        _sessions.pop(token, None)
        return None
    return session


def logout(token: str | None) -> None:
    if token:
        _sessions.pop(token, None)


def require_admin(request: Request) -> str:
    if not settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configura ADMIN_PASSWORD en el .env para usar el panel.",
        )
    token = request.cookies.get(COOKIE_NAME)
    session = get_session(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesion expirada",
        )
    return session["username"]


def totp_enabled() -> bool:
    return bool(settings.admin_totp_secret)


def generate_totp_uri(account: str = "admin") -> tuple[str, str]:
    secret = settings.admin_totp_secret or pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=account, issuer_name="Finanzas Admin")
    return secret, uri


def clear_all_sessions() -> None:
    _sessions.clear()
