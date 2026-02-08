from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.config import config
from app.models import User
from app.repositories import UserRepository


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
            return None

        if not self.verify_password(password, user.password_hash):
            return None

        self.user_repo.update_last_login(user.id)
        return user

    @staticmethod
    def generate_token(user: User) -> str:
        """Generate JWT token for authenticated user."""
        now = datetime.utcnow()
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "iat": now,
            "exp": now + timedelta(hours=config.JWT_TTL_HOURS),
        }
        return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
            if "sub" not in payload or "role" not in payload:
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None