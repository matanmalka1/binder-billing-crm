from __future__ import annotations

from typing import Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.users.models.user import User, UserRole
from app.utils.time_utils import utcnow


class UserRepository(BaseRepository[User]):
    """Data access layer for User entities."""

    model = User

    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_id(self, entity_id: int) -> Optional[User]:
        return self.db.scalars(select(User).where(User.id == entity_id)).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve user by email."""
        return self.db.scalars(select(User).where(User.email == email)).first()

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> list[User]:
        """List users with pagination."""
        stmt = self._apply_list_filters(
            select(User),
            is_active=is_active,
            search=search,
        ).order_by(User.id.asc())
        stmt = self.apply_pagination(stmt, page, page_size)
        return list(self.db.scalars(stmt).all())

    def count(
        self, is_active: Optional[bool] = None, search: Optional[str] = None
    ) -> int:
        """Count users."""
        stmt = self._apply_list_filters(
            select(func.count(User.id)),
            is_active=is_active,
            search=search,
        )
        return self.db.scalar(stmt)

    def _apply_list_filters(
        self,
        stmt,
        *,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ):
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )
        return stmt

    def list_by_ids(self, user_ids: list[int]) -> list[User]:
        """Batch fetch users by a list of IDs (single query)."""
        if not user_ids:
            return []
        return self.db.scalars(select(User).where(User.id.in_(user_ids))).all()

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
        self.db.execute(
            update(User).where(User.id == user_id).values(last_login_at=utcnow())
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

    def set_password_and_bump_token(
        self, user_id: int, password_hash: str
    ) -> Optional[User]:
        """Update password hash and invalidate active tokens."""
        user = self.get_by_id(user_id)
        if not user:
            return None

        user.password_hash = password_hash
        user.token_version += 1
        self.db.flush()
        return user
