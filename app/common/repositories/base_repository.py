from __future__ import annotations

from typing import ClassVar, Generic, TypeVar

from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from app.utils.time_utils import utcnow

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic CRUD base for SQLAlchemy ORM repositories.

    Opt in by setting:
        model = SomeModel

    Subclasses that do not set `model` continue to override methods directly —
    fully backward-compatible.

    New methods use SQLAlchemy 2.0 select() / scalars() style.
    Legacy helpers (_update_entity, _update_status, _locked_first, _paginate)
    are kept unchanged for existing callers.
    """

    model: ClassVar[type[ModelType]]

    def __init__(self, db: Session):
        self.db = db

    # ── Generic CRUD (SQLAlchemy 2.0) ────────────────────────────────────────

    def get_by_id(self, entity_id: int) -> ModelType | None:
        stmt = select(self.model).where(
            self.model.id == entity_id,
            self.model.deleted_at.is_(None),
        )
        return self.db.scalars(stmt).first()

    def get_by_id_for_update(self, entity_id: int) -> ModelType | None:
        stmt = (
            select(self.model)
            .where(
                self.model.id == entity_id,
                self.model.deleted_at.is_(None),
            )
            .with_for_update()
        )
        return self.db.scalars(stmt).first()

    def add(self, entity: ModelType) -> ModelType:
        """Add a pre-built entity to the session and flush."""
        self.db.add(entity)
        self.db.flush()
        return entity

    def build_and_add(self, **kwargs) -> ModelType:
        """Instantiate model from kwargs, add to session, flush. Use when no domain defaults needed."""
        entity = self.model(**kwargs)
        self.db.add(entity)
        self.db.flush()
        return entity

    def update_entity(
        self, entity, *, touch_updated_at: bool = False, **fields
    ) -> ModelType | None:
        """Named update_entity to avoid collision with domain-specific update() methods."""
        return self._update_entity(entity, touch_updated_at=touch_updated_at, **fields)

    def _soft_delete_entity(
        self, entity_id: int, deleted_by: int | None = None
    ) -> bool:
        """Generic soft-delete. Named with underscore so domain soft_delete() does not override it."""
        entity = self.get_by_id(entity_id)
        if not entity:
            return False
        entity.deleted_at = utcnow()
        if deleted_by is not None and hasattr(entity, "deleted_by"):
            entity.deleted_by = deleted_by
        self.db.flush()
        return True

    # ── Sort / pagination (SA 2.0 select stmt style) ─────────────────────────

    @staticmethod
    def apply_sort(stmt, sort_by: str, order: str, sortable_fields: dict):
        """
        Apply ORDER BY to a select() statement.

        sortable_fields: {"field_name": Model.column, ...}
        Falls back to first entry when sort_by is unknown.
        Returns stmt unchanged if sortable_fields is empty.
        """
        if not sortable_fields:
            return stmt
        fallback = next(iter(sortable_fields.values()))
        col = sortable_fields.get(sort_by, fallback)
        return stmt.order_by(desc(col) if order == "desc" else asc(col))

    @staticmethod
    def apply_pagination(stmt, page: int, page_size: int):
        """Apply offset/limit to a select() statement."""
        offset = (page - 1) * page_size
        return stmt.offset(offset).limit(page_size)

    # ── Legacy helpers (unchanged — backward compat) ──────────────────────────

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
        """Apply offset/limit pagination to a SQLAlchemy query (legacy query API)."""
        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size).all()
