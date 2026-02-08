import hashlib
from datetime import datetime, timedelta
from typing import Optional

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
        """Hash password using SHA-256 (production should use bcrypt)."""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        return AuthService.hash_password(password) == password_hash

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
        payload = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(hours=config.JWT_TTL_HOURS),
        }
        return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and validate JWT token."""
        try:
            return jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None