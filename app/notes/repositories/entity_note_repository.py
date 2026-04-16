from typing import Optional

from sqlalchemy.orm import Session

from app.notes.models.entity_note import EntityNote
from app.utils.time_utils import utcnow_aware


class EntityNoteRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        entity_type: str,
        entity_id: int,
        note: str,
        created_by: Optional[int] = None,
    ) -> EntityNote:
        obj = EntityNote(
            entity_type=entity_type,
            entity_id=entity_id,
            note=note,
            created_by=created_by,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def list_for_entity(
        self,
        entity_type: str,
        entity_id: int,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[EntityNote], int]:
        base = (
            self.db.query(EntityNote)
            .filter(
                EntityNote.entity_type == entity_type,
                EntityNote.entity_id == entity_id,
                EntityNote.deleted_at.is_(None),
            )
        )
        from sqlalchemy import func
        total = base.with_entities(func.count()).scalar() or 0
        items = (
            base.order_by(EntityNote.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_by_id(self, note_id: int) -> Optional[EntityNote]:
        return (
            self.db.query(EntityNote)
            .filter(EntityNote.id == note_id, EntityNote.deleted_at.is_(None))
            .first()
        )

    def update(self, note_id: int, note: str) -> Optional[EntityNote]:
        obj = self.get_by_id(note_id)
        if not obj:
            return None
        obj.note = note
        self.db.flush()
        return obj

    def soft_delete(self, note_id: int, deleted_by: int) -> bool:
        obj = self.get_by_id(note_id)
        if not obj:
            return False
        obj.deleted_at = utcnow_aware()
        obj.deleted_by = deleted_by
        self.db.flush()
        return True
