from datetime import UTC, datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.config import config
from app.core.logging_config import get_logger
from app.users.models.user_audit_log import AuditAction, AuditStatus
from app.users.models.user import User
from app.users.repositories.user_repository import UserRepository
from app.users.services.audit_log_service import AuditLogService

logger = get_logger(__name__)


class AuthService:
    """Authentication and authorization business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.audit_log_service = AuditLogService(db)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against bcrypt hash."""
        return bcrypt.checkpw(password.encode(), password_hash.encode())

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user by email and password."""
        user = self.user_repo.get_by_email(email)

        if not user:
            logger.warning(f"Failed login attempt for email: {email}")
            self.audit_log_service.log(
                action=AuditAction.LOGIN_FAILURE,
                status=AuditStatus.FAILURE,
                email=email,
                reason="user_not_found",
            )
            return None

        if not user.is_active:
            logger.warning(f"Inactive user login attempt for email: {email}")
            self.audit_log_service.log(
                action=AuditAction.LOGIN_FAILURE,
                status=AuditStatus.FAILURE,
                target_user_id=user.id,
                email=email,
                reason="inactive_user",
            )
            return None

        if not self.verify_password(password, user.password_hash):
            logger.warning(f"Invalid password for email: {email}")
            self.audit_log_service.log(
                action=AuditAction.LOGIN_FAILURE,
                status=AuditStatus.FAILURE,
                target_user_id=user.id,
                email=email,
                reason="invalid_password",
            )
            return None

        self.user_repo.update_last_login(user.id)
        self.audit_log_service.log(
            action=AuditAction.LOGIN_SUCCESS,
            status=AuditStatus.SUCCESS,
            actor_user_id=user.id,
            target_user_id=user.id,
            email=user.email,
        )
        logger.info(f"Successful login for user: {email}")
        return user

    def logout(self, user: User) -> None:
        """
        Invalidate all active tokens for the user by bumping token_version.

        This ensures that any token — whether sent via cookie or Authorization header —
        is rejected on the next request, even before the JWT expiry time.
        """
        self.user_repo.bump_token_version(user.id)
        self.audit_log_service.log(
            action=AuditAction.LOGOUT,
            status=AuditStatus.SUCCESS,
            actor_user_id=user.id,
            target_user_id=user.id,
            email=user.email,
        )
        logger.info(f"User logged out and token invalidated: {user.email}")

    @staticmethod
    def generate_token(user: User, ttl_hours: int | None = None) -> str:
        """
        Generate JWT token for authenticated user.

        Embeds token_version so the server can invalidate tokens
        without a token blacklist.
        """
        ttl = ttl_hours if ttl_hours is not None else config.JWT_TTL_HOURS
        now = datetime.now(UTC)
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "tv": user.token_version,
            "iat": now,
            "exp": now + timedelta(hours=ttl),
        }
        return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and validate JWT token. Returns payload or None."""
        try:
            payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
            required_fields = {"sub", "email", "role", "exp", "iat"}
            if not required_fields.issubset(payload):
                logger.debug("Token missing required fields")
                return None
            return payload
        except jwt.ExpiredSignatureError:
            logger.debug("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid token: {e}")
            return None
