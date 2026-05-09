from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.utils.time_utils import utcnow

ModelType = TypeVar("ModelType")


@dataclass(frozen=True)
class Page(Generic[ModelType]):
    items: list[ModelType]
    total: int
    page: int
    page_size: int


def _has_column(model: type[Any], column_name: str) -> bool:
    return hasattr(model, column_name)


def _apply_not_deleted(stmt, model: type[Any]):
    if not _has_column(model, "deleted_at"):
        return stmt
    return stmt.where(model.deleted_at.is_(None))


def _apply_sort(stmt, sort_by: str | None, order: str, sortable_fields: dict):
    if not sortable_fields:
        return stmt
    fallback = next(iter(sortable_fields.values()))
    column = sortable_fields.get(sort_by, fallback)
    direction = desc if order == "desc" else asc
    return stmt.order_by(direction(column))


def _apply_pagination(stmt, page: int, page_size: int):
    return stmt.offset((page - 1) * page_size).limit(page_size)


def _count_stmt(stmt):
    return select(func.count()).select_from(stmt.order_by(None).subquery())


class BaseRepository(Generic[ModelType]):
    """
    Generic CRUD base for SQLAlchemy ORM repositories.

    Opt in by setting:
        model = SomeModel

    Subclasses that do not set `model` continue to override methods directly —
    fully backward-compatible.

    Methods use SQLAlchemy 2.0 select() / scalars() style.
    Legacy helpers (_update_entity, _update_status, _locked_first, _paginate)
    are kept unchanged for existing callers.
    """

    model: ClassVar[type[ModelType]]

    def __init__(self, db: Session):
        self.db = db

    # Generic CRUD

    def select_base(self, *, include_deleted: bool = False):
        stmt = select(self.model)
        return stmt if include_deleted else _apply_not_deleted(stmt, self.model)

    def get(self, entity_id: int, *, include_deleted: bool = False) -> ModelType | None:
        stmt = self.select_base(include_deleted=include_deleted).where(
            self.model.id == entity_id
        )
        return self.db.scalars(stmt).first()

    def get_by_id(self, entity_id: int) -> ModelType | None:
        return self.get(entity_id)

    def get_by_id_for_update(self, entity_id: int) -> ModelType | None:
        stmt = self.select_base().where(self.model.id == entity_id).with_for_update()
        return self.db.scalars(stmt).first()

    def get_multi(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "asc",
        sortable_fields: dict[str, Any] | None = None,
        include_deleted: bool = False,
    ) -> list[ModelType]:
        stmt = self.select_base(include_deleted=include_deleted)
        stmt = _apply_sort(stmt, sort_by, sort_order, sortable_fields or {})
        stmt = _apply_pagination(stmt, page, page_size)
        return list(self.db.scalars(stmt).all())

    def count(self, *, include_deleted: bool = False) -> int:
        stmt = self.select_base(include_deleted=include_deleted)
        return self.db.scalar(_count_stmt(stmt)) or 0

    def paginate(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "asc",
        sortable_fields: dict[str, Any] | None = None,
        include_deleted: bool = False,
    ) -> Page[ModelType]:
        items = self.get_multi(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            sortable_fields=sortable_fields,
            include_deleted=include_deleted,
        )
        return Page(
            items=items,
            total=self.count(include_deleted=include_deleted),
            page=page,
            page_size=page_size,
        )

    def add(self, entity: ModelType) -> ModelType:
        """Add a pre-built entity to the session and flush."""
        self.db.add(entity)
        self.db.flush()
        return entity

    def create(self, *args, **kwargs) -> ModelType:
        if args:
            raise TypeError("BaseRepository.create accepts keyword fields only")
        return self.build_and_add(**kwargs)

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

    def update(self, entity_id: int, **fields) -> ModelType | None:
        return self.update_entity(self.get(entity_id), **fields)

    def soft_delete(self, entity_id: int, deleted_by: int | None = None) -> bool:
        if not _has_column(self.model, "deleted_at"):
            return self.hard_delete(entity_id)
        entity = self.get_by_id(entity_id)
        if not entity:
            return False
        entity.deleted_at = utcnow()
        if deleted_by is not None and hasattr(entity, "deleted_by"):
            entity.deleted_by = deleted_by
        self.db.flush()
        return True

    def _soft_delete_entity(
        self, entity_id: int, deleted_by: int | None = None
    ) -> bool:
        return BaseRepository.soft_delete(self, entity_id, deleted_by)

    def delete(
        self,
        entity_id: int,
        deleted_by: int | None = None,
        *,
        hard: bool = False,
    ) -> bool:
        if not hard and _has_column(self.model, "deleted_at"):
            return self.soft_delete(entity_id, deleted_by)
        return self.hard_delete(entity_id)

    def hard_delete(self, entity_id: int) -> bool:
        entity = self.get(entity_id, include_deleted=True)
        if not entity:
            return False
        self.db.delete(entity)
        self.db.flush()
        return True

    # Sort / pagination compatibility

    apply_sort = staticmethod(_apply_sort)
    apply_pagination = staticmethod(_apply_pagination)

    # Legacy helpers

    def _update_entity(
        self,
        entity,
        *,
        touch_updated_at: bool = False,
        **fields,
    ):
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
