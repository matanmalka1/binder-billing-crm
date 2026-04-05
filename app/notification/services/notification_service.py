"""
NotificationService — public facade used by API and cross-domain callers.

Delegates delivery to NotificationSendService.
Handles read-state and list operations directly.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import Binder
from app.businesses.models.business import Business
from app.businesses.repositories.business_repository import BusinessRepository
from app.core.logging_config import get_logger

logger = get_logger(__name__)
from app.notification.models.notification import NotificationChannel, NotificationSeverity, NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.schemas.notification_schemas import NotificationResponse
from app.notification.services.notification_send_service import NotificationSendService


def _enrich(notification: object, name_map: dict[int, str]) -> NotificationResponse:
    resp = NotificationResponse.model_validate(notification)
    resp.business_name = name_map.get(notification.business_id)
    return resp


class NotificationService:
    """Public facade — use this class from API routers and other domains."""

    def __init__(self, db: Session):
        self.db = db
        self.notification_repo = NotificationRepository(db)
        self.business_repo = BusinessRepository(db)
        self._send_svc = NotificationSendService(db)

    # ── Named trigger helpers ─────────────────────────────────────────────────

    def notify_binder_received(self, binder: Binder, business: Business) -> bool:
        name = business.business_name or "לקוח"
        content = (
            f"שלום {name},\n\n"
            f"תיק מספר {binder.binder_number} התקבל במשרד בתאריך {binder.period_start}.\n\n"
            f"בברכה"
        )
        return self._send_svc.send_notification(
            business_id=business.id,
            trigger=NotificationTrigger.BINDER_RECEIVED,
            content=content,
            binder_id=binder.id,
        )

    def notify_ready_for_pickup(self, binder: Binder, business: Business) -> bool:
        name = business.business_name or "לקוח"
        content = (
            f"שלום {name},\n\n"
            f"תיק מספר {binder.binder_number} מוכן לאיסוף מהמשרד.\n\n"
            f"בברכה"
        )
        return self._send_svc.send_notification(
            business_id=business.id,
            trigger=NotificationTrigger.BINDER_READY_FOR_PICKUP,
            content=content,
            binder_id=binder.id,
        )

    def notify_payment_reminder(
        self,
        business_id: int,
        reminder_text: str,
        triggered_by: Optional[int] = None,
    ) -> bool:
        return self._send_svc.send_notification(
            business_id=business_id,
            trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
            content=reminder_text,
            triggered_by=triggered_by,
        )

    def bulk_notify(
        self,
        business_ids: list[int],
        template: str,
        channel: NotificationChannel = NotificationChannel.EMAIL,
        trigger: NotificationTrigger = NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        triggered_by: Optional[int] = None,
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> dict:
        return self._send_svc.bulk_notify(
            business_ids=business_ids,
            template=template,
            channel=channel,
            trigger=trigger,
            triggered_by=triggered_by,
            severity=severity,
        )

    def send_notification(
        self,
        business_id: int,
        trigger: NotificationTrigger,
        content: str,
        binder_id: Optional[int] = None,
        triggered_by: Optional[int] = None,
        preferred_channel: str = "email",
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> bool:
        return self._send_svc.send_notification(
            business_id=business_id,
            trigger=trigger,
            content=content,
            binder_id=binder_id,
            triggered_by=triggered_by,
            preferred_channel=preferred_channel,
            severity=severity,
        )

    # ── Read / list ───────────────────────────────────────────────────────────

    def list_paginated(
        self, page: int = 1, page_size: int = 20, business_id: Optional[int] = None
    ) -> tuple:
        items, total = self.notification_repo.list_paginated(
            page=page, page_size=page_size, business_id=business_id
        )
        name_map = self._build_name_map(items)
        return [_enrich(n, name_map) for n in items], total

    def list_recent(self, limit: int = 20, business_id: Optional[int] = None):
        items = self.notification_repo.list_recent(limit=limit, business_id=business_id)
        name_map = self._build_name_map(items)
        return [_enrich(n, name_map) for n in items]

    def _build_name_map(self, notifications: list) -> dict[int, str]:
        ids = list({n.business_id for n in notifications})
        businesses = self.business_repo.list_by_ids(ids)
        return {b.id: b.full_name for b in businesses}

    def count_unread(self, business_id: Optional[int] = None) -> int:
        return self.notification_repo.count_unread(business_id=business_id)

    def mark_read(self, notification_ids: list[int]) -> int:
        return self.notification_repo.mark_read(notification_ids)

    def mark_all_read(self, business_id: Optional[int] = None) -> int:
        return self.notification_repo.mark_all_read(business_id)
