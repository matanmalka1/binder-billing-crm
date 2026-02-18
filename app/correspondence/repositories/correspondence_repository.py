from datetime import datetime
from typing import Optional

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

    def list_by_client(self, client_id: int) -> list[Correspondence]:
        return (
            self.db.query(Correspondence)
            .filter(Correspondence.client_id == client_id)
            .order_by(Correspondence.occurred_at.desc())
            .all()
        )