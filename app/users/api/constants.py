from app.config import settings

COOKIE_NAME = "access_token"
COOKIE_SAMESITE = "none" if settings.APP_ENV == "production" else "lax"
REMEMBER_ME_TTL_MULTIPLIER = 2
