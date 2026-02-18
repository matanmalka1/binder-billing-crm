from typing import Optional

from sqlalchemy.orm import Session

from app.users.models.user import User, UserRole
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

    def list(self, page: int = 1, page_size: int = 20) -> list[User]:
        """List users with pagination."""
        offset = (page - 1) * page_size
        return (
            self.db.query(User)
            .order_by(User.id.asc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    def count(self) -> int:
        """Count users."""
        return self.db.query(User).count()

    def create(
        self,
        full_name: str,
        email: str,
        password_hash: str,
        role: UserRole,
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

    def update(self, user_id: int, **fields) -> Optional[User]:
        """Update user fields."""
        user = self.get_by_id(user_id)
        if not user:
            return None

        for key, value in fields.items():
            setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def activate(self, user_id: int) -> Optional[User]:
        """Activate user."""
        return self.update(user_id, is_active=True)

    def deactivate_and_bump_token(self, user_id: int) -> Optional[User]:
        """Deactivate user and invalidate active tokens."""
        user = self.get_by_id(user_id)
        if not user:
            return None

        user.is_active = False
        user.token_version += 1
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_password_and_bump_token(self, user_id: int, password_hash: str) -> Optional[User]:
        """Update password hash and invalidate active tokens."""
        user = self.get_by_id(user_id)
        if not user:
            return None

        user.password_hash = password_hash
        user.token_version += 1
        self.db.commit()
        self.db.refresh(user)
        return user
