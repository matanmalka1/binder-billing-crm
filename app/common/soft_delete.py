"""Soft-delete mixin shared by domain models."""

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, declarative_mixin, declared_attr, mapped_column


@declarative_mixin
class SoftDeletableMixin:
    @declared_attr
    def deleted_at(cls) -> Mapped[datetime | None]:
        return mapped_column(nullable=True)

    @declared_attr
    def deleted_by(cls) -> Mapped[int | None]:
        return mapped_column(ForeignKey("users.id"), nullable=True)

    @declared_attr
    def restored_at(cls) -> Mapped[datetime | None]:
        return mapped_column(nullable=True)

    @declared_attr
    def restored_by(cls) -> Mapped[int | None]:
        return mapped_column(ForeignKey("users.id"), nullable=True)

    @classmethod
    def active_clause(cls):
        return cls.deleted_at.is_(None)
