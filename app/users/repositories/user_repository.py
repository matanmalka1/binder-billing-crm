from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.users.models.user import User, UserRole
from app.utils.time_utils import utcnow


class UserRepository(BaseRepository):
    """Data access layer for User entities."""

    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
    ) -> list[User]:
        """List users with pagination."""
        query = self.db.query(User)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        return self._paginate(query.order_by(User.id.asc()), page, page_size)

    def count(self, is_active: Optional[bool] = None) -> int:
        """Count users."""
        query = self.db.query(User)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        return query.count()

    def list_by_ids(self, user_ids: list[int]) -> list[User]:
        """Batch fetch users by a list of IDs (single query)."""
        if not user_ids:
            return []
        return self.db.query(User).filter(User.id.in_(user_ids)).all()

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
        self.db.flush()
        return user

    def update_last_login(self, user_id: int) -> None:
        """Update last login timestamp."""
        self.db.query(User).filter(User.id == user_id).update(
            {"last_login_at": utcnow()}
        )
        self.db.flush()

    def update(self, user_id: int, **fields) -> Optional[User]:
        """Update user fields."""
        user = self.get_by_id(user_id)
        return self._update_entity(user, **fields)

    def activate(self, user_id: int) -> Optional[User]:
        """Activate user."""
        return self.update(user_id, is_active=True)

    def bump_token_version(self, user_id: int) -> Optional[User]:
        """Invalidate all active tokens for a user without changing any other field."""
        user = self.get_by_id(user_id)
        if not user:
            return None

        user.token_version += 1
        self.db.flush()
        return user

    def deactivate_and_bump_token(self, user_id: int) -> Optional[User]:
        """Deactivate user and invalidate active tokens."""
        user = self.get_by_id(user_id)
        if not user:
            return None

        user.is_active = False
        user.token_version += 1
        self.db.flush()
        return user

    def set_password_and_bump_token(self, user_id: int, password_hash: str) -> Optional[User]:
        """Update password hash and invalidate active tokens."""
        user = self.get_by_id(user_id)
        if not user:
            return None

        user.password_hash = password_hash
        user.token_version += 1
        self.db.flush()
        return user
