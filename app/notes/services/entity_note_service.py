from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.notes.models.entity_note import EntityNote
from app.notes.repositories.entity_note_repository import EntityNoteRepository

_NOT_FOUND = "NOTE.NOT_FOUND"


class EntityNoteService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EntityNoteRepository(db)

    def _get_or_raise(self, note_id: int, entity_type: str, entity_id: int) -> EntityNote:
        note = self.repo.get_by_id(note_id)
        if not note or note.entity_type != entity_type or note.entity_id != entity_id:
            raise NotFoundError(
                f"הערה {note_id} לא נמצאה",
                _NOT_FOUND,
            )
        return note

    def list_notes(
        self,
        entity_type: str,
        entity_id: int,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[EntityNote], int]:
        return self.repo.list_for_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            page=page,
            page_size=page_size,
        )

    def add_note(
        self,
        entity_type: str,
        entity_id: int,
        note: str,
        created_by: Optional[int] = None,
    ) -> EntityNote:
        return self.repo.create(
            entity_type=entity_type,
            entity_id=entity_id,
            note=note,
            created_by=created_by,
        )

    def update_note(
        self,
        note_id: int,
        entity_type: str,
        entity_id: int,
        note: str,
        actor_id: int,
    ) -> EntityNote:
        obj = self._get_or_raise(note_id, entity_type, entity_id)
        if obj.created_by != actor_id:
            raise ForbiddenError("אין הרשאה לעדכן הערה זו", "NOTE.FORBIDDEN")
        updated = self.repo.update(note_id, note)
        if not updated:
            raise NotFoundError(f"הערה {note_id} לא נמצאה", _NOT_FOUND)
        return updated

    def delete_note(
        self,
        note_id: int,
        entity_type: str,
        entity_id: int,
        actor_id: int,
    ) -> None:
        self._get_or_raise(note_id, entity_type, entity_id)
        self.repo.soft_delete(note_id, deleted_by=actor_id)
