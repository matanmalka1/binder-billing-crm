from datetime import datetime
from typing import Literal, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.correspondence.models.correspondence import Correspondence, CorrespondenceType
from app.utils.time_utils import utcnow_aware


class CorrespondenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: int,                          # PRIMARY anchor — always required
        correspondence_type: CorrespondenceType,
        subject: str,
        occurred_at: datetime,
        created_by: int,
        business_id: Optional[int] = None,       # OPTIONAL — UI grouping only
        contact_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Correspondence:
        entry = Correspondence(
            client_id=client_id,
            business_id=business_id,
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

    def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        client_id: Optional[int] = None,
        business_id: Optional[int] = None,
        correspondence_type: Optional[CorrespondenceType] = None,
        contact_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        sort_dir: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[Correspondence], int]:
        base = self.db.query(Correspondence).filter(
            Correspondence.deleted_at.is_(None),
        )

        # At least one of client_id / business_id should always be provided
        if client_id is not None:
            base = base.filter(Correspondence.client_id == client_id)
        if business_id is not None:
            base = base.filter(Correspondence.business_id == business_id)
        if correspondence_type is not None:
            base = base.filter(Correspondence.correspondence_type == correspondence_type)
        if contact_id is not None:
            base = base.filter(Correspondence.contact_id == contact_id)
        if from_date is not None:
            base = base.filter(Correspondence.occurred_at >= from_date)
        if to_date is not None:
            base = base.filter(Correspondence.occurred_at <= to_date)

        total = base.with_entities(func.count()).scalar() or 0
        order = (
            Correspondence.occurred_at.desc()
            if sort_dir == "desc"
            else Correspondence.occurred_at.asc()
        )
        offset = (page - 1) * page_size
        items = base.order_by(order).offset(offset).limit(page_size).all()
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
        entry.deleted_at = utcnow_aware()
        entry.deleted_by = deleted_by
        self.db.commit()
        return True