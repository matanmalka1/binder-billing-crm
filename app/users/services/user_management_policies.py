from app.users.models.user import UserRole

IMMUTABLE_UPDATE_FIELDS = {
    "email",
    "id",
    "token_version",
    "created_at",
    "last_login_at",
    "is_active",
}


def ensure_advisor(actor_role: UserRole) -> None:
    if actor_role != UserRole.ADVISOR:
        raise PermissionError("Only advisors can manage users")


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

