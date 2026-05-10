from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, NamedTuple, Optional

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


class ClientWorkQueueProfile(NamedTuple):
    name: str
    office_number: Optional[int]


def urgency(due_date: date, today: date) -> WorkQueueUrgency:
    days = (due_date - today).days
    if days < 0:
        return WorkQueueUrgency.OVERDUE
    if days <= APPROACHING_DAYS:
        return WorkQueueUrgency.APPROACHING
    return WorkQueueUrgency.UPCOMING


def load_client_profiles(
    db: Session, client_record_ids: Iterable[int]
) -> Dict[int, ClientWorkQueueProfile]:
    """Fetch dashboard identity fields only for the client ids present in the result set."""
    ids = list(client_record_ids)
    if not ids:
        return {}
    stmt = (
        select(
            ClientRecord.id,
            LegalEntity.official_name,
            ClientRecord.office_client_number,
        )
        .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
        .where(ClientRecord.id.in_(ids), ClientRecord.deleted_at.is_(None))
    )
    return {
        row[0]: ClientWorkQueueProfile(name=row[1], office_number=row[2])
        for row in db.execute(stmt).all()
    }


class WorkQueueContext:
    def __init__(self, db: Session, today: date):
        self.db = db
        self.today = today
        self._client_profiles: Optional[Dict[int, ClientWorkQueueProfile]] = None
        self._pending_ids: set[int] = set()

    def register_client_id(self, client_record_id: int) -> None:
        """Collect a client id for lazy batch name resolution."""
        if self._client_profiles is None:
            self._pending_ids.add(client_record_id)

    def _resolve_profiles(self) -> Dict[int, ClientWorkQueueProfile]:
        if self._client_profiles is None:
            self._client_profiles = load_client_profiles(self.db, self._pending_ids)
        return self._client_profiles

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
        if client_record_id is not None:
            self.register_client_id(client_record_id)
        client_profile = (
            self._resolve_profiles().get(client_record_id)
            if client_record_id is not None
            else None
        )
        return WorkQueueItem(
            source_type=source_type,
            source_id=source_id,
            label=label,
            due_date=due_date,
            urgency=item_urgency or urgency(due_date, self.today),
            client_record_id=client_record_id,
            client_name=client_profile.name if client_profile else None,
            client_office_number=(
                client_profile.office_number if client_profile else None
            ),
            business_id=business_id,
            payload=payload,
        )
