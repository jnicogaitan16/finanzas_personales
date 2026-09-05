from __future__ import annotations

import secrets
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from config import settings
from db.models import User

COOKIE_NAME = "finanzas_session"
_MAX_SESSIONS = 50
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


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def login(
    db: Session,
    username: str,
    password: str,
    client_ip: str = "",
) -> str | None:
    """Authenticate against the users table. Returns session token or None."""
    if client_ip and _is_locked_out(client_ip):
        return None

    user = db.query(User).filter(User.nombre == username).one_or_none()
    if user is None or not user.password_hash:
        if client_ip:
            _record_failed_attempt(client_ip)
        return None

    if not _verify_password(password, user.password_hash):
        if client_ip:
            _record_failed_attempt(client_ip)
        return None

    if client_ip:
        _clear_failed_attempts(client_ip)

    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "user_id": user.id,
        "username": user.nombre,
        "grupo_id": user.grupo_id,
        "created": _now(),
    }
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


def require_auth(request: Request) -> dict[str, Any]:
    """Returns the full session dict with user_id, username, grupo_id."""
    token = request.cookies.get(COOKIE_NAME)
    session = get_session(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesion expirada",
        )
    return session


# Keep backward compat name for existing endpoints during migration
require_admin = require_auth


def get_visible_user_ids(session: dict[str, Any], db: Session) -> list[int]:
    """Retorna los IDs de usuarios que el logueado puede ver.

    - Si tiene grupo: todos los miembros del grupo
    - Si no tiene grupo: solo él mismo
    """
    grupo_id = session.get("grupo_id")
    if grupo_id:
        return [
            u.id for u in db.query(User).filter(User.grupo_id == grupo_id).all()
        ]
    return [session["user_id"]]


def create_session_for_user(user: User) -> str:
    """Create a session token for an already-authenticated user (e.g. OAuth)."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "user_id": user.id,
        "username": user.nombre,
        "grupo_id": user.grupo_id,
        "created": _now(),
    }
    if len(_sessions) > _MAX_SESSIONS:
        _sessions.popitem(last=False)
    return token


def clear_all_sessions() -> None:
    _sessions.clear()
