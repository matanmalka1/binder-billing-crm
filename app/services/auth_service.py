from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.config import config
from app.core.logging import get_logger
from app.models import User
from app.repositories import UserRepository

logger = get_logger(__name__)


class AuthService:
    """Authentication and authorization business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

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

        if not user or not user.is_active:
            logger.warning(f"Failed login attempt for email: {email}")
            return None

        if not self.verify_password(password, user.password_hash):
            logger.warning(f"Invalid password for email: {email}")
            return None

        self.user_repo.update_last_login(user.id)
        logger.info(f"Successful login for user: {email}")
        return user

    @staticmethod
    def generate_token(user: User) -> str:
        """
        Generate JWT token for authenticated user.
        
        Token includes explicit expiration (iat + exp).
        """
        now = datetime.utcnow()
        expiration = now + timedelta(hours=config.JWT_TTL_HOURS)
        
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "iat": now,
            "exp": expiration,
        }
        
        token = jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")
        logger.info(f"Generated token for user {user.id}, expires at {expiration}")
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
            if "sub" not in payload or "role" not in payload:
                logger.warning("Token missing required fields")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Expired token rejected")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None