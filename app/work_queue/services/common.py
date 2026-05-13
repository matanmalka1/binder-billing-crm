from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, NamedTuple, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.work_queue.schemas.work_queue import (
    WorkQueueItem,
    WorkQueueSourceSummary,
    WorkQueueSourceType,
    WorkQueueUrgency,
)

APPROACHING_DAYS = 7
IMPORTANT_DAYS = 21
UPCOMING_WINDOW_DAYS = 21

SOURCE_TYPE_LABELS = {
    WorkQueueSourceType.VAT_WORK_ITEM: 'דוח מע"מ',
    WorkQueueSourceType.ANNUAL_REPORT: "דוח שנתי",
    WorkQueueSourceType.ADVANCE_PAYMENT: "מקדמה",
    WorkQueueSourceType.CHARGE: "חיוב לא שולם",
    WorkQueueSourceType.BINDER: "קלסר",
    WorkQueueSourceType.TASK: "משימה",
}

STATUS_LABELS = {
    WorkQueueSourceType.VAT_WORK_ITEM: {
        "pending_materials": "ממתין לחומרים",
        "material_received": "חומרים התקבלו",
        "data_entry_in_progress": "בהקלדה",
        "ready_for_review": "מוכן לבדיקה",
        "filed": "הוגש",
        "canceled": "בוטל",
        "archived": "בארכיון",
    },
    WorkQueueSourceType.ANNUAL_REPORT: {
        "not_started": "טרם התחיל",
        "collecting_docs": "איסוף מסמכים",
        "docs_complete": "מסמכים הושלמו",
        "in_preparation": "בהכנה",
        "pending_client": "ממתין ללקוח",
        "submitted": "הוגש",
        "amended": "מתוקן",
        "accepted": "התקבל",
        "assessment_issued": "שומה הוצאה",
        "objection_filed": "השגה הוגשה",
        "closed": "סגור",
        "canceled": "בוטל",
    },
    WorkQueueSourceType.ADVANCE_PAYMENT: {
        "pending": "ממתינה",
        "partial": "שולמה חלקית",
        "paid": "שולמה",
    },
    WorkQueueSourceType.CHARGE: {
        "draft": "טיוטה",
        "issued": "הונפק",
        "paid": "שולם",
        "canceled": "בוטל",
    },
    WorkQueueSourceType.BINDER: {
        "in_office": "במשרד",
        "closed_in_office": "סגור במשרד",
        "archived_in_office": "בארכיון במשרד",
        "ready_for_pickup": "מוכן לאיסוף",
        "returned": "הוחזר",
    },
    WorkQueueSourceType.TASK: {
        "open": "פתוחה",
        "in_progress": "בטיפול",
        "done": "הושלמה",
        "canceled": "בוטלה",
    },
}


class ClientWorkQueueProfile(NamedTuple):
    name: str
    office_number: Optional[int]


def urgency(due_date: date, today: date) -> WorkQueueUrgency:
    days = (due_date - today).days
    if days < 0:
        return WorkQueueUrgency.OVERDUE
    if days <= APPROACHING_DAYS:
        return WorkQueueUrgency.APPROACHING
    if days <= IMPORTANT_DAYS:
        return WorkQueueUrgency.IMPORTANT
    return WorkQueueUrgency.UPCOMING


def normalize_source_domain(value: str | None) -> WorkQueueSourceType | None:
    if not value:
        return None
    try:
        return WorkQueueSourceType(value)
    except ValueError:
        return None


def source_key(source_type: WorkQueueSourceType, source_id: int) -> tuple[str, int]:
    return (source_type.value, source_id)


def source_route(source_type: WorkQueueSourceType, source_id: int) -> str | None:
    if source_type == WorkQueueSourceType.VAT_WORK_ITEM:
        return f"/tax/vat/{source_id}"
    if source_type == WorkQueueSourceType.ANNUAL_REPORT:
        return f"/tax/reports/{source_id}"
    if source_type == WorkQueueSourceType.ADVANCE_PAYMENT:
        return "/tax/advance-payments"
    if source_type == WorkQueueSourceType.CHARGE:
        return "/charges"
    if source_type == WorkQueueSourceType.BINDER:
        return "/binders"
    return None


def display_status_label(
    source_type: WorkQueueSourceType, status: str | None
) -> str | None:
    if status is None:
        return None
    return STATUS_LABELS.get(source_type, {}).get(status, status)


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
        self._pending_ids.add(client_record_id)

    def _resolve_profiles(self) -> Dict[int, ClientWorkQueueProfile]:
        missing = self._pending_ids - set(self._client_profiles or {})
        if missing:
            new_profiles = load_client_profiles(self.db, missing)
            if self._client_profiles is None:
                self._client_profiles = new_profiles
            else:
                self._client_profiles.update(new_profiles)
        elif self._client_profiles is None:
            self._client_profiles = {}
        return self._client_profiles

    def item(
        self,
        source_type: WorkQueueSourceType,
        source_id: int,
        title: str,
        due_date: date,
        client_record_id: Optional[int],
        *,
        business_id: Optional[int] = None,
        item_urgency: Optional[WorkQueueUrgency] = None,
        status_label: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> WorkQueueItem:
        if client_record_id is not None:
            self.register_client_id(client_record_id)
        client_profile = (
            self._resolve_profiles().get(client_record_id)
            if client_record_id is not None
            else None
        )
        return WorkQueueItem(
            id=f"{source_type.value}:{source_id}",
            source_type=source_type,
            source_id=source_id,
            title=title,
            description=description,
            type_label=SOURCE_TYPE_LABELS.get(source_type, source_type.value),
            status_label=display_status_label(source_type, status_label),
            due_date=due_date,
            urgency=item_urgency or urgency(due_date, self.today),
            client_record_id=client_record_id,
            client_name=client_profile.name if client_profile else None,
            office_client_number=(
                client_profile.office_number if client_profile else None
            ),
            business_id=business_id,
            source_summary=WorkQueueSourceSummary(
                source_type=source_type.value,
                source_id=source_id,
                label=title,
                route=source_route(source_type, source_id),
            ),
            metadata=metadata,
        )
