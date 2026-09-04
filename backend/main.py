import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session

from admin.router import router as admin_router
from config import settings
from logging_config import setup_logging
from db.session import get_db
from db.users_seed import seed_authorized_users

setup_logging()
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_authorized_users()
    # Auto-registrar ingresos fijos del mes actual como Movimientos
    try:
        from db.session import SessionLocal
        from services.ingresos import sincronizar_ingresos_fijos
        db = SessionLocal()
        creados = sincronizar_ingresos_fijos(db)
        if creados:
            logger.info("Ingresos fijos sincronizados: %d movimientos creados", creados)
        db.close()
    except Exception:
        logger.exception("Error sincronizando ingresos fijos")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(admin_router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "frame-ancestors 'none'"
    )
    return response


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
