"""Soft-delete mixin shared by domain models."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import declarative_mixin


@declarative_mixin
class SoftDeletableMixin:
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    restored_at = Column(DateTime, nullable=True)
    restored_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    @classmethod
    def active_clause(cls):
        return cls.deleted_at.is_(None)
