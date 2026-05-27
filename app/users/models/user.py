from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.enum_utils import pg_enum
from app.utils.time_utils import utcnow


class UserRole(str, PyEnum):
    ADVISOR = "advisor"
    SECRETARY = "secretary"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(60), nullable=False)

    role: Mapped[UserRole] = mapped_column(pg_enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    token_version: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")

    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
