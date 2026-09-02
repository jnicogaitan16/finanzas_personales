from sqlalchemy.orm import Session

from config import settings
from db.models import User
from db.session import SessionLocal


def parse_authorized_users(raw: str) -> list[tuple[str, str]]:
    pares: list[tuple[str, str]] = []
    for fragmento in raw.split(","):
        fragmento = fragmento.strip()
        if not fragmento or ":" not in fragmento:
            continue
        nombre, telefono = fragmento.rsplit(":", 1)
        nombre = nombre.strip()
        telefono = "".join(ch for ch in telefono if ch.isdigit())
        if nombre and telefono:
            pares.append((nombre, telefono))
    return pares


def seed_authorized_users(db: Session | None = None) -> int:
    pares = parse_authorized_users(settings.authorized_users)
    if not pares:
        return 0
    own_session = db is None
    session = db or SessionLocal()
    creados = 0
    try:
        for nombre, telefono in pares:
            existente = (
                session.query(User).filter(User.numero_whatsapp == telefono).one_or_none()
            )
            if existente is None:
                session.add(User(nombre=nombre, numero_whatsapp=telefono))
                creados += 1
            elif existente.nombre != nombre:
                existente.nombre = nombre
        session.commit()
    except Exception:
        session.rollback()
    finally:
        if own_session:
            session.close()
    return creados
