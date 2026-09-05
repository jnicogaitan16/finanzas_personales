from __future__ import annotations

from sqlalchemy.orm import Session


def seed_authorized_users(db: Session | None = None) -> int:
    """No-op. Users are now created via the registration endpoint."""
    return 0
