from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://evolution:evolution@localhost:5433/finanzas"
    app_name: str = "finanzas-bot"
    authorized_users: str = ""
    admin_user: str = "admin"
    admin_password: str = ""
    admin_password_hash: str = ""
    admin_totp_secret: str = ""
    admin_session_hours: int = 24
    groq_api_key: str = ""
    redis_url: str = "redis://localhost:6379/1"

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
