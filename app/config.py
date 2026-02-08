import os
from typing import Literal


class Config:
    """Application configuration from environment variables."""

    APP_ENV: Literal["local", "test", "staging", "production"] = os.getenv("APP_ENV", "local")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./binder_crm_test.db" if os.getenv("APP_ENV") == "test" else "sqlite:///./binder_crm.db"
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
