import hashlib
import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.infrastructure.notifications import EmailChannel
from app.users.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from app.users.repositories.user_repository import UserRepository
from app.users.services.auth_service import AuthService
from app.users.services.user_management_policies import validate_password
from app.utils.time_utils import utcnow

logger = get_logger(__name__)

_FORGOT_MESSAGE = "אם קיים משתמש עם האימייל הזה, נשלחו הוראות לאיפוס סיסמה"
_RESET_MESSAGE = "הסיסמה אופסה בהצלחה"
_INVALID_TOKEN_MESSAGE = "קישור איפוס הסיסמה אינו תקין או שפג תוקפו"


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class PasswordResetService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = PasswordResetTokenRepository(db)
        self.email_channel = EmailChannel(
            enabled=settings.NOTIFICATIONS_ENABLED,
            api_key=settings.BREVO_API_KEY,
            api_url=settings.BREVO_API_URL,
            from_address=settings.EMAIL_FROM_ADDRESS,
            from_name=settings.EMAIL_FROM_NAME,
        )

    def request_password_reset(
        self,
        email: str,
        *,
        requested_ip: str | None,
        user_agent: str | None,
    ) -> str:
        normalized_email = email.strip().lower()
        user = self.user_repo.get_by_email(normalized_email)
        if user is None or not user.is_active:
            return _FORGOT_MESSAGE

        self.token_repo.invalidate_unused_tokens_for_user(user.id)

        raw_token = secrets.token_urlsafe(32)
        self.token_repo.create(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=utcnow()
            + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
            requested_ip=requested_ip,
            user_agent=user_agent,
        )
        self.db.commit()

        reset_url = f"{settings.FRONTEND_PASSWORD_RESET_URL}?token={raw_token}"
        if settings.PASSWORD_RESET_DEV_LOG:
            logger.info("[DEV ONLY] Password reset URL for %s: %s", normalized_email, reset_url)

        content = (
            f"שלום {user.full_name},\n\n"
            "התקבלה בקשה לאיפוס הסיסמה שלך.\n"
            f"לאיפוס הסיסמה יש להיכנס לקישור הבא: {reset_url}\n\n"
            f"הקישור תקף למשך {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} דקות.\n"
            "אם לא ביקשת לאפס סיסמה, אפשר להתעלם מההודעה."
        )
        ok, error = self.email_channel.send(
            user.email,
            content,
            subject="איפוס סיסמה",
        )
        if not ok:
            logger.error("Password reset email failed for %s: %s", normalized_email, error)

        return _FORGOT_MESSAGE

    def reset_password(self, raw_token: str, new_password: str) -> str:
        validate_password(new_password)
        token_record = self.token_repo.get_valid_by_token_hash(_hash_token(raw_token))
        if token_record is None:
            raise AppError(_INVALID_TOKEN_MESSAGE, "AUTH.INVALID_PASSWORD_RESET_TOKEN", 400)

        user = self.user_repo.get_by_id(token_record.user_id)
        if user is None or not user.is_active:
            raise AppError(_INVALID_TOKEN_MESSAGE, "AUTH.INVALID_PASSWORD_RESET_TOKEN", 400)

        if not self.token_repo.mark_used(token_record.id):
            raise AppError(_INVALID_TOKEN_MESSAGE, "AUTH.INVALID_PASSWORD_RESET_TOKEN", 400)

        user.password_hash = AuthService.hash_password(new_password)
        user.token_version += 1
        self.db.commit()
        return _RESET_MESSAGE
