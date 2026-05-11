from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy.orm import Session

from app.users.models.user import UserRole
from app.utils.time_utils import israel_today
from app.work_queue.schemas.work_queue import (
    WorkQueueItem,
    WorkQueueSourceType,
    WorkQueueUrgency,
)
from app.work_queue.services.work_queue_service import WorkQueueService

_ATTENTION_URGENCIES = frozenset(
    {
        WorkQueueUrgency.OVERDUE,
        WorkQueueUrgency.APPROACHING,
        WorkQueueUrgency.IMPORTANT,
    }
)

_URGENCY_ORDER = {
    WorkQueueUrgency.OVERDUE: 0,
    WorkQueueUrgency.APPROACHING: 1,
    WorkQueueUrgency.IMPORTANT: 2,
    WorkQueueUrgency.UPCOMING: 3,
}

_MAX_ITEMS = 7
_FALLBACK_MIN = 3


def _sort_key(item: WorkQueueItem) -> tuple:
    return (_URGENCY_ORDER.get(item.urgency, 9), item.due_date or date.max)


def _href(item: WorkQueueItem) -> str:
    st = item.source_type
    if st == WorkQueueSourceType.VAT_FILING:
        return f"/tax/vat/{item.source_id}"
    if st == WorkQueueSourceType.ANNUAL_REPORT:
        return f"/tax/reports/{item.source_id}"
    if st == WorkQueueSourceType.ADVANCE_PAYMENT:
        return "/tax/advance-payments"
    if st == WorkQueueSourceType.UNPAID_CHARGE:
        return "/charges"
    if st == WorkQueueSourceType.STALE_BINDER:
        return "/binders"
    if st == WorkQueueSourceType.TASK:
        return "/tasks"
    return "/"


def _reason(item: WorkQueueItem) -> Optional[str]:
    st = item.source_type
    payload = item.payload or {}
    if st == WorkQueueSourceType.VAT_FILING:
        return "דוח מע״מ לא הוגש"
    if st == WorkQueueSourceType.ANNUAL_REPORT:
        return "דוח שנתי ממתין להגשה"
    if st == WorkQueueSourceType.ADVANCE_PAYMENT:
        remaining = payload.get("remaining_amount")
        if remaining:
            return f"יתרה לתשלום: ₪{remaining}"
        return "מקדמה ממתינה לתשלום"
    if st == WorkQueueSourceType.UNPAID_CHARGE:
        return "חיוב שלא שולם"
    if st == WorkQueueSourceType.STALE_BINDER:
        return None  # label already contains the waiting duration
    if st == WorkQueueSourceType.TASK:
        return payload.get("description") or "משימה פתוחה"
    return None


def _format_ils(value: str) -> Optional[str]:
    try:
        d = Decimal(str(value))
        formatted = f"{d:,.2f}".rstrip("0").rstrip(".")
        return f"₪{formatted}"
    except (InvalidOperation, ValueError):
        return None


def _amount(item: WorkQueueItem) -> Optional[str]:
    if item.source_type == WorkQueueSourceType.UNPAID_CHARGE:
        raw = (item.payload or {}).get("amount")
        if raw:
            return _format_ils(raw)
    return None


def _to_attention_item(item: WorkQueueItem, today: date) -> dict:
    days_delta = (item.due_date - today).days if item.due_date is not None else 0
    return {
        "id": f"{item.source_type}:{item.source_id}",
        "source_type": item.source_type,
        "source_id": item.source_id,
        "title": item.label,
        "client_name": item.client_name,
        "due_date": item.due_date,
        "days_delta": days_delta,
        "reason": _reason(item),
        "amount": _amount(item),
        "urgency": item.urgency,
        "href": _href(item),
    }


def _is_attention_eligible(item: WorkQueueItem) -> bool:
    """Tasks require a due_date and must be in an attention urgency tier."""
    if item.source_type == WorkQueueSourceType.TASK:
        return item.due_date is not None and item.urgency in _ATTENTION_URGENCIES
    return True


class DashboardAttentionService:
    def __init__(self, db: Session):
        self.db = db

    def build(
        self,
        user_role: Optional[UserRole] = None,
        reference_date: Optional[date] = None,
    ) -> list[dict]:
        if user_role != UserRole.ADVISOR:
            return []
        today = reference_date or israel_today()
        all_items = WorkQueueService(self.db).list_items(limit=200)
        all_items = [i for i in all_items if _is_attention_eligible(i)]

        attention = [i for i in all_items if i.urgency in _ATTENTION_URGENCIES]

        if len(attention) < _FALLBACK_MIN:
            upcoming = [i for i in all_items if i.urgency == WorkQueueUrgency.UPCOMING]
            attention += upcoming[: _FALLBACK_MIN - len(attention)]

        attention.sort(key=_sort_key)
        return [_to_attention_item(i, today) for i in attention[:_MAX_ITEMS]]
