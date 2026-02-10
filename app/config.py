import os
from pathlib import Path
from typing import Literal


try:
    from dotenv import load_dotenv
except Exception:  
    load_dotenv = None 


def _load_env_files() -> None:
    """
    Load dotenv from env-specific file before Config is initialized.

    Existing environment variables always win (override=False).
    """
    if load_dotenv is None:
        return

    root_dir = Path(__file__).resolve().parents[1]

    raw_app_env = (os.getenv("APP_ENV") or "development").strip().lower()
    app_env = "development" if raw_app_env == "local" else raw_app_env
    os.environ["APP_ENV"] = app_env

    env_file = os.getenv("ENV_FILE")
    if env_file:
        load_dotenv(dotenv_path=env_file, override=False)
    else:
        if app_env == "production":
            selected = root_dir / ".env.production"
        elif app_env == "development":
            selected = root_dir / ".env.development"
        else:
            selected = root_dir / f".env.{app_env}"

        if selected.exists():
            load_dotenv(dotenv_path=selected, override=False)


_load_env_files()


class Config:
    """Application configuration from environment variables."""

    APP_ENV: Literal["development", "test", "staging", "production"] = (
        os.getenv("APP_ENV") or "development"
    )  # type: ignore[assignment]
    PORT: int = int(os.getenv("PORT", "8000"))
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./binder_crm_test.db" if APP_ENV == "test" else "sqlite:///./binder_crm.db"
    )

    _jwt_secret = os.getenv("JWT_SECRET")
    if not _jwt_secret:
        raise ValueError("JWT_SECRET must be set")
    JWT_SECRET: str = _jwt_secret
    
    JWT_TTL_HOURS: int = int(os.getenv("JWT_TTL_HOURS", "8"))

    CORS_ALLOWED_ORIGINS: list[str] = os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
    ).split(",")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Phase 2 placeholders
    NOTIFICATIONS_ENABLED: bool = os.getenv("NOTIFICATIONS_ENABLED", "false").lower() == "true"
    INVOICE_PROVIDER_BASE_URL: str = os.getenv("INVOICE_PROVIDER_BASE_URL", "")
    INVOICE_PROVIDER_API_KEY: str = os.getenv("INVOICE_PROVIDER_API_KEY", "")


config = Config()
