from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://evolution:evolution@localhost:5433/finanzas"
    app_name: str = "finanzas-bot"
    admin_session_hours: int = 24
    groq_api_key: str = ""
    redis_url: str = "redis://localhost:6379/1"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/api/oauth/google/callback"
    registro_abierto: bool = False

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
