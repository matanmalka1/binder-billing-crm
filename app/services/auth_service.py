from datetime import UTC, datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.config import config
from app.core.logging import get_logger
from app.models import AuditAction, AuditStatus, User
from app.repositories import UserRepository
from app.services.audit_log_service import AuditLogService

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

    @staticmethod
    def generate_token(user: User, ttl_hours: int | None = None) -> str:
        """
        Generate JWT token for authenticated user.
        
        Token includes explicit expiration (iat + exp).
        """
        now = datetime.now(UTC)
        effective_ttl = ttl_hours or config.JWT_TTL_HOURS
        expiration = now + timedelta(hours=effective_ttl)
        
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "tv": user.token_version,
            "iat": now,
            "exp": expiration,
        }
        
        token = jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")
        logger.info(
            f"Generated token for user {user.id}, expires at {expiration}"
        )
        return token

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """
        Decode and validate JWT token.
        
        Enforces expiration checking.
        Returns None if token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                config.JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_exp": True},  # Enforce expiration
            )
            
            # Validate required fields
            if "sub" not in payload or "role" not in payload or "tv" not in payload:
                logger.warning("Token missing required fields")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Expired token rejected")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None
