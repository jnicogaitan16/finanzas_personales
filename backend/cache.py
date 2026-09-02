"""Redis cache for state that must survive backend restarts.

Falls back to in-memory dicts when Redis is unavailable so the app
still works in dev without Redis running.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis

from config import settings

logger = logging.getLogger(__name__)

_PREFIX = "finanzas:"
_r: redis.Redis | None = None


def _get_redis() -> redis.Redis | None:
    global _r
    if _r is not None:
        return _r
    if not settings.redis_url:
        return None
    try:
        _r = redis.from_url(settings.redis_url, decode_responses=True)
        _r.ping()
        logger.info("Redis conectado: %s", settings.redis_url)
        return _r
    except Exception:
        logger.warning("Redis no disponible, usando memoria")
        _r = None
        return None


# ---------- Message dedup ----------

_MSG_IDS_MEM: dict[str, None] = {}
_MSG_IDS_KEY = f"{_PREFIX}msg_ids"
_MSG_IDS_MAX = 500
_MSG_IDS_TTL = 3600  # 1 hour


def msg_ya_visto(message_id: str | None) -> bool:
    if not message_id:
        return False
    r = _get_redis()
    if r:
        try:
            if r.sismember(_MSG_IDS_KEY, message_id):
                return True
            r.sadd(_MSG_IDS_KEY, message_id)
            if r.scard(_MSG_IDS_KEY) > _MSG_IDS_MAX:
                # Trim: remove oldest by converting to sorted set would be complex;
                # instead just expire the whole set periodically
                r.expire(_MSG_IDS_KEY, _MSG_IDS_TTL)
            return False
        except Exception:
            pass
    # Fallback: in-memory
    if message_id in _MSG_IDS_MEM:
        return True
    _MSG_IDS_MEM[message_id] = None
    if len(_MSG_IDS_MEM) > _MSG_IDS_MAX:
        oldest = next(iter(_MSG_IDS_MEM))
        del _MSG_IDS_MEM[oldest]
    return False


# ---------- Pendientes (command disambiguation) ----------

_PENDIENTES_MEM: dict[int, dict[str, Any]] = {}
_PENDIENTES_PREFIX = f"{_PREFIX}pendiente:"
_PENDIENTES_TTL = 300  # 5 minutes


def get_pendiente(user_id: int) -> dict[str, Any] | None:
    r = _get_redis()
    if r:
        try:
            data = r.get(f"{_PENDIENTES_PREFIX}{user_id}")
            if data:
                return json.loads(data)
            return None
        except Exception:
            pass
    return _PENDIENTES_MEM.get(user_id)


def set_pendiente(user_id: int, pendiente: dict[str, Any]) -> None:
    r = _get_redis()
    if r:
        try:
            r.setex(
                f"{_PENDIENTES_PREFIX}{user_id}",
                _PENDIENTES_TTL,
                json.dumps(pendiente),
            )
            return
        except Exception:
            pass
    _PENDIENTES_MEM[user_id] = pendiente


def del_pendiente(user_id: int) -> None:
    r = _get_redis()
    if r:
        try:
            r.delete(f"{_PENDIENTES_PREFIX}{user_id}")
        except Exception:
            pass
    _PENDIENTES_MEM.pop(user_id, None)


def clear_pendientes() -> None:
    r = _get_redis()
    if r:
        try:
            keys = r.keys(f"{_PENDIENTES_PREFIX}*")
            if keys:
                r.delete(*keys)
        except Exception:
            pass
    _PENDIENTES_MEM.clear()
