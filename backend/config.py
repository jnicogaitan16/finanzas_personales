from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://evolution:evolution@localhost:5433/finanzas"
    app_name: str = "finanzas-bot"
    evolution_api_url: str = ""
    evolution_api_key: str = ""
    evolution_instance: str = "finanzas"
    evolution_webhook_url: str = "http://backend:8000/webhook/evolution"
    authorized_users: str = ""
    admin_user: str = "admin"
    admin_password: str = ""
    admin_totp_secret: str = ""
    admin_session_hours: int = 24
    groq_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
