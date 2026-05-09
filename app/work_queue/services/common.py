from __future__ import annotations

from datetime import date
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.work_queue.schemas.work_queue import (
    WorkQueueItem,
    WorkQueueSourceType,
    WorkQueueUrgency,
)

APPROACHING_DAYS = 7
UPCOMING_WINDOW_DAYS = 14


def urgency(due_date: date, today: date) -> WorkQueueUrgency:
    days = (due_date - today).days
    if days < 0:
        return WorkQueueUrgency.OVERDUE
    if days <= APPROACHING_DAYS:
        return WorkQueueUrgency.APPROACHING
    return WorkQueueUrgency.UPCOMING


def load_client_name_map(db: Session) -> Dict[int, str]:
    stmt = (
        select(ClientRecord.id, LegalEntity.official_name)
        .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
        .where(ClientRecord.deleted_at.is_(None))
    )
    return {row[0]: row[1] for row in db.execute(stmt).all()}


class WorkQueueContext:
    def __init__(self, db: Session, today: date):
        self.db = db
        self.today = today
        self.client_names = load_client_name_map(db)

    def item(
        self,
        source_type: WorkQueueSourceType,
        source_id: int,
        label: str,
        due_date: date,
        client_record_id: Optional[int],
        *,
        business_id: Optional[int] = None,
        item_urgency: Optional[WorkQueueUrgency] = None,
        payload: Optional[dict] = None,
    ) -> WorkQueueItem:
        return WorkQueueItem(
            source_type=source_type,
            source_id=source_id,
            label=label,
            due_date=due_date,
            urgency=item_urgency or urgency(due_date, self.today),
            client_record_id=client_record_id,
            client_name=self.client_names.get(client_record_id)
            if client_record_id is not None
            else None,
            business_id=business_id,
            payload=payload,
        )
