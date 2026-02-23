from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.correspondence.models.correspondence import Correspondence, CorrespondenceType


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
        query = (
            self.db.query(Correspondence)
            .filter(Correspondence.client_id == client_id)
            .order_by(Correspondence.occurred_at.desc())
        )

        total = query.with_entities(func.count()).scalar() or 0
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total
