from app.config import config


COOKIE_NAME = "access_token"
COOKIE_SAMESITE = "none" if config.APP_ENV == "production" else "lax"
REMEMBER_ME_TTL_MULTIPLIER = 2
