from app.core.exceptions import AppError, ForbiddenError
from app.users.models.user import UserRole

MIN_PASSWORD_LENGTH = 8

IMMUTABLE_UPDATE_FIELDS = {
    "id",
    "token_version",
    "created_at",
    "last_login_at",
    "is_active",
}


def ensure_advisor(actor_role: UserRole) -> None:
    if actor_role != UserRole.ADVISOR:
        raise ForbiddenError("רק יועצים יכולים לנהל משתמשים", "USER.FORBIDDEN")


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AppError("הסיסמה חייבת להכיל לפחות 8 תווים", "USER.INVALID_PASSWORD")
