from __future__ import annotations

import secrets
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from secrets import compare_digest
from typing import Any

import bcrypt
import pyotp
from fastapi import HTTPException, Request, status

from config import settings

COOKIE_NAME = "finanzas_session"
_MAX_SESSIONS = 20
_MAX_FAILED_ATTEMPTS = 10
_LOCKOUT_SECONDS = 300  # 5 minutes

_sessions: OrderedDict[str, dict[str, Any]] = OrderedDict()
_failed_attempts: dict[str, list[datetime]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_locked_out(ip: str) -> bool:
    attempts = _failed_attempts.get(ip, [])
    cutoff = _now() - timedelta(seconds=_LOCKOUT_SECONDS)
    recent = [t for t in attempts if t > cutoff]
    _failed_attempts[ip] = recent
    return len(recent) >= _MAX_FAILED_ATTEMPTS


def _record_failed_attempt(ip: str) -> None:
    _failed_attempts.setdefault(ip, []).append(_now())


def _clear_failed_attempts(ip: str) -> None:
    _failed_attempts.pop(ip, None)


def _check_password(password: str) -> bool:
    if settings.admin_password_hash:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            settings.admin_password_hash.encode("utf-8"),
        )
    return compare_digest(password, settings.admin_password)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def login(
    username: str,
    password: str,
    totp_code: str | None = None,
    client_ip: str = "",
) -> str | None:
    if not (settings.admin_password or settings.admin_password_hash):
        return None
    if client_ip and _is_locked_out(client_ip):
        return None
    if not (compare_digest(username, settings.admin_user) and _check_password(password)):
        if client_ip:
            _record_failed_attempt(client_ip)
        return None
    if settings.admin_totp_secret:
        if not totp_code:
            if client_ip:
                _record_failed_attempt(client_ip)
            return None
        totp = pyotp.TOTP(settings.admin_totp_secret)
        if not totp.verify(totp_code.strip(), valid_window=1):
            if client_ip:
                _record_failed_attempt(client_ip)
            return None
    if client_ip:
        _clear_failed_attempts(client_ip)
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
    if not (settings.admin_password or settings.admin_password_hash):
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
