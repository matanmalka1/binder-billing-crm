from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.correspondence.models.correspondence import Correspondence, CorrespondenceType
from app.utils.time import utcnow


class CorrespondenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: int,
        correspondence_type: CorrespondenceType,
        subject: str,
        occurred_at: datetime,
        created_by: int,
        contact_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Correspondence:
        entry = Correspondence(
            client_id=client_id,
            contact_id=contact_id,
            correspondence_type=correspondence_type,
            subject=subject,
            notes=notes,
            occurred_at=occurred_at,
            created_by=created_by,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list_by_client_paginated(
        self, client_id: int, *, page: int, page_size: int
    ) -> tuple[list[Correspondence], int]:
        base = self.db.query(Correspondence).filter(
            Correspondence.client_id == client_id,
            Correspondence.deleted_at.is_(None),
        )

        total = base.with_entities(func.count()).scalar() or 0
        offset = (page - 1) * page_size
        items = base.order_by(Correspondence.occurred_at.desc()).offset(offset).limit(page_size).all()
        return items, total

    def get_by_id(self, entry_id: int) -> Optional[Correspondence]:
        return (
            self.db.query(Correspondence)
            .filter(Correspondence.id == entry_id, Correspondence.deleted_at.is_(None))
            .first()
        )

    def update(self, entry_id: int, **fields) -> Optional[Correspondence]:
        entry = self.get_by_id(entry_id)
        if not entry:
            return None
        for key, value in fields.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def soft_delete(self, entry_id: int, deleted_by: int) -> bool:
        entry = self.get_by_id(entry_id)
        if not entry:
            return False
        entry.deleted_at = utcnow()
        entry.deleted_by = deleted_by
        self.db.commit()
        return True
