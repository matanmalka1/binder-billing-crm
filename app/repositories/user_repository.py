from typing import Optional

from sqlalchemy.orm import Session

from app.models import User
from app.utils.time import utcnow


class UserRepository:
    """Data access layer for User entities."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def create(
        self,
        full_name: str,
        email: str,
        password_hash: str,
        role: str,
        phone: Optional[str] = None,
    ) -> User:
        """Create new user."""
        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            role=role,
            phone=phone,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_last_login(self, user_id: int) -> None:
        """Update last login timestamp."""
        self.db.query(User).filter(User.id == user_id).update(
            {"last_login_at": utcnow()}
        )
        self.db.commit()
