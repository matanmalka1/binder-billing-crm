from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.utils.time_utils import utcnow


class BaseRepository:
    """Shared repository helpers to reduce repetition."""

    def __init__(self, db: Session):
        self.db = db

    def _update_entity(
        self,
        entity,
        *,
        touch_updated_at: bool = False,
        **fields,
    ):
        """
        Apply field updates, optionally touching an `updated_at` timestamp.

        The caller is responsible for fetching the entity (e.g., via get_by_id).
        Returns the flushed entity (in-session object) or None if entity is falsy.
        Commit is deferred to the service layer or the get_db() safety net.
        """
        if not entity:
            return None

        for key, value in fields.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

        if touch_updated_at and hasattr(entity, "updated_at"):
            entity.updated_at = utcnow()

        self.db.flush()
        return entity

    def _update_status(
        self,
        entity,
        new_status,
        *,
        touch_updated_at: bool = False,
        **additional_fields,
    ):
        """Set status and delegate to _update_entity for remaining fields."""
        if not entity:
            return None
        entity.status = new_status
        return self._update_entity(
            entity,
            touch_updated_at=touch_updated_at,
            **additional_fields,
        )

    def _locked_first(self, query):
        """Apply SELECT … FOR UPDATE and return the first result.

        On PostgreSQL this acquires a row-level exclusive lock until db.commit().
        On SQLite (used in tests) with_for_update() is accepted but is a no-op —
        tests can only verify code paths, not true blocking semantics.
        """
        return query.with_for_update().first()

    @staticmethod
    def _paginate(query, page: int, page_size: int):
        """Apply offset/limit pagination to a SQLAlchemy query."""
        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size).all()
