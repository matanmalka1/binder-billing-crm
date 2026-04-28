"""NotificationService — public facade used by API and cross-domain callers."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import Binder
from app.businesses.repositories.business_repository import BusinessRepository
from app.core.logging_config import get_logger
from app.notification.models.notification import NotificationChannel, NotificationSeverity, NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.schemas.notification_schemas import NotificationResponse
from app.notification.services.messages import (
    ANNUAL_REPORT_CLIENT_REMINDER_NOTIFICATION_CONTENT,
    BINDER_READY_FOR_PICKUP_NOTIFICATION_CONTENT,
    BINDER_RECEIVED_NOTIFICATION_CONTENT,
    FALLBACK_CLIENT_NAME,
    PICKUP_REMINDER_NOTIFICATION_CONTENT,
)
from app.notification.services.notification_send_service import NotificationSendService

logger = get_logger(__name__)


def _enrich(notification: object, name_map: dict[int, str]) -> NotificationResponse:
    resp = NotificationResponse.model_validate(notification)
    if notification.business_id is not None:
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

    def notify_binder_received(self, binder: Binder, client_record_id: int) -> bool:
        person = self._send_svc._get_client(client_record_id)
        name = (person.full_name if person else None) or FALLBACK_CLIENT_NAME
        content = BINDER_RECEIVED_NOTIFICATION_CONTENT.format(
            name=name,
            binder_number=binder.binder_number,
            period_start=binder.period_start,
        )
        return self._send_svc.send_client_notification(
            client_record_id=client_record_id,
            trigger=NotificationTrigger.BINDER_RECEIVED,
            content=content,
            binder_id=binder.id,
        )

    def notify_ready_for_pickup(self, binder: Binder, client_record_id: int) -> bool:
        person = self._send_svc._get_client(client_record_id)
        name = (person.full_name if person else None) or FALLBACK_CLIENT_NAME
        content = BINDER_READY_FOR_PICKUP_NOTIFICATION_CONTENT.format(
            name=name,
            binder_number=binder.binder_number,
        )
        return self._send_svc.send_client_notification(
            client_record_id=client_record_id,
            trigger=NotificationTrigger.BINDER_READY_FOR_PICKUP,
            content=content,
            binder_id=binder.id,
        )

    def notify_pickup_reminder(self, binder: Binder, client_record_id: int, triggered_by: Optional[int] = None) -> bool:
        person = self._send_svc._get_client(client_record_id)
        name = (person.full_name if person else None) or FALLBACK_CLIENT_NAME
        content = PICKUP_REMINDER_NOTIFICATION_CONTENT.format(
            name=name,
            binder_number=binder.binder_number,
        )
        return self._send_svc.send_client_notification(
            client_record_id=client_record_id,
            trigger=NotificationTrigger.PICKUP_REMINDER,
            content=content,
            binder_id=binder.id,
            triggered_by=triggered_by,
        )

    def notify_annual_report_client_reminder(
        self,
        client_record_id: int,
        annual_report_id: int,
        tax_year: int,
        triggered_by: Optional[int] = None,
    ) -> bool:
        person = self._send_svc._get_client(client_record_id)
        name = (person.full_name if person else None) or FALLBACK_CLIENT_NAME
        content = ANNUAL_REPORT_CLIENT_REMINDER_NOTIFICATION_CONTENT.format(
            name=name,
            tax_year=tax_year,
        )
        return self._send_svc.send_client_notification(
            client_record_id=client_record_id,
            trigger=NotificationTrigger.ANNUAL_REPORT_CLIENT_REMINDER,
            content=content,
            annual_report_id=annual_report_id,
            triggered_by=triggered_by,
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

    def notify_client_reminder(self, client_record_id: int, reminder_text: str) -> bool:
        return self._send_svc.send_client_reminder(client_record_id, reminder_text)

    def notify_client_record_reminder(self, client_record_id: int, reminder_text: str) -> bool:
        return self._send_svc.send_client_record_reminder(client_record_id, reminder_text)

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
        self,
        page: int = 1,
        page_size: int = 20,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> tuple:
        items, total = self.notification_repo.list_paginated(
            page=page,
            page_size=page_size,
            client_record_id=client_record_id,
            business_id=business_id,
        )
        name_map = self._build_name_map(items)
        return [_enrich(n, name_map) for n in items], total

    def list_recent(
        self,
        limit: int = 20,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ):
        items = self.notification_repo.list_recent(
            limit=limit,
            client_record_id=client_record_id,
            business_id=business_id,
        )
        name_map = self._build_name_map(items)
        return [_enrich(n, name_map) for n in items]

    def _build_name_map(self, notifications: list) -> dict[int, str]:
        """Build business_id → business_name map. Skips client-only notifications (business_id=None)."""
        ids = [n.business_id for n in notifications if n.business_id is not None]
        if not ids:
            return {}
        businesses = self.business_repo.list_by_ids(list(set(ids)))
        return {
            b.id: getattr(b, "business_name", None) or getattr(b, "full_name", None)
            for b in businesses
        }

    def count_unread(
        self,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> int:
        return self.notification_repo.count_unread(
            client_record_id=client_record_id,
            business_id=business_id,
        )

    def mark_read(self, notification_ids: list[int]) -> int:
        return self.notification_repo.mark_read(notification_ids)

    def mark_all_read(
        self,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> int:
        return self.notification_repo.mark_all_read(
            client_record_id=client_record_id,
            business_id=business_id,
        )
