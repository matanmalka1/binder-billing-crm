"""
Notification service — email (SendGrid) + WhatsApp (360dialog when configured).

WhatsApp sends when WHATSAPP_API_KEY is set; falls back to email otherwise.
The service is non-blocking: it always returns True so calling code
is never interrupted by a notification failure.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.config import config
from app.infrastructure.notifications import EmailChannel, WhatsAppChannel
from app.binders.models.binder import Binder
from app.businesses.models.business import Business
from app.clients.models.client import Client
from app.notification.models.notification import NotificationChannel, NotificationSeverity, NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository
from app.core import get_logger

logger = get_logger(__name__)

_SUBJECTS: dict[NotificationTrigger, str] = {
    NotificationTrigger.BINDER_RECEIVED: "התיק שלך התקבל במשרד",
    NotificationTrigger.BINDER_READY_FOR_PICKUP: "התיק שלך מוכן לאיסוף",
    NotificationTrigger.MANUAL_PAYMENT_REMINDER: "תזכורת תשלום",
}


class NotificationService:
    """Notification engine — email via SendGrid; WhatsApp via 360dialog when configured."""

    def __init__(self, db: Session):
        self.db = db
        self.notification_repo = NotificationRepository(db)
        self.email = EmailChannel(
            enabled=config.NOTIFICATIONS_ENABLED,
            api_key=config.SENDGRID_API_KEY,
            from_address=config.EMAIL_FROM_ADDRESS,
            from_name=config.EMAIL_FROM_NAME,
        )
        self.whatsapp = WhatsAppChannel(
            api_key=config.WHATSAPP_API_KEY,
            api_url=config.WHATSAPP_API_URL,
            from_number=config.WHATSAPP_FROM_NUMBER,
        )

    def _get_business_and_client(self, business_id: int) -> tuple[Business, Client] | None:
        """Load business + owner client contact details in a single query."""
        row = (
            self.db.query(Business, Client)
            .join(Client, Client.id == Business.client_id)
            .filter(
                Business.id == business_id,
                Business.deleted_at.is_(None),
                Client.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            return None
        return row

    def _resolve_recipient_name(self, business: Business) -> str:
        """Prefer business display name, fallback to owner's full name."""
        if business.business_name:
            return business.business_name

        client = getattr(business, "client", None)
        if client and getattr(client, "full_name", None):
            return client.full_name

        business_and_client = self._get_business_and_client(business.id)
        if business_and_client:
            _business, owner_client = business_and_client
            if owner_client.full_name:
                return owner_client.full_name
        return "לקוח"

    def notify_binder_received(self, binder: Binder, business: Business) -> bool:
        recipient_name = self._resolve_recipient_name(business)
        content = (
            f"שלום {recipient_name},\n\n"
            f"תיק מספר {binder.binder_number} התקבל במשרד בתאריך {binder.received_at}.\n\n"
            f"בברכה"
        )
        return self.send_notification(
            business_id=business.id,
            trigger=NotificationTrigger.BINDER_RECEIVED,
            content=content,
            binder_id=binder.id,
        )

    def notify_ready_for_pickup(self, binder: Binder, business: Business) -> bool:
        recipient_name = self._resolve_recipient_name(business)
        content = (
            f"שלום {recipient_name},\n\n"
            f"תיק מספר {binder.binder_number} מוכן לאיסוף מהמשרד.\n\n"
            f"בברכה"
        )
        return self.send_notification(
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
        return self.send_notification(
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
        """Send a notification to a list of businesses. Returns {sent, failed} counts."""
        sent = 0
        failed = 0
        for business_id in business_ids:
            ok = self.send_notification(
                business_id=business_id,
                trigger=trigger,
                content=template,
                triggered_by=triggered_by,
                preferred_channel=channel.value,
                severity=severity,
            )
            if ok:
                sent += 1
            else:
                failed += 1
        return {"sent": sent, "failed": failed}

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
        """
        Persist + send a notification (WhatsApp if configured, otherwise email).

        Never raises — always returns True so callers are not interrupted.
        """
        try:
            business_and_client = self._get_business_and_client(business_id)
            if not business_and_client:
                logger.warning("send_notification: business %s not found", business_id)
                return True
            _business, client = business_and_client

            subject = _SUBJECTS.get(trigger, "הודעה ממערכת ניהול התיקים")

            # Try WhatsApp first if requested and configured
            if preferred_channel == "whatsapp" and self.whatsapp.enabled and client.phone:
                success, error = self.whatsapp.send(client.phone, content)
                if success:
                    notification = self.notification_repo.create(
                        business_id=business_id,
                        binder_id=binder_id,
                        trigger=trigger,
                        channel=NotificationChannel.WHATSAPP,
                        recipient=client.phone,
                        content_snapshot=content,
                        triggered_by=triggered_by,
                        severity=severity,
                    )
                    self.notification_repo.mark_sent(notification.id)
                    logger.info("WhatsApp sent | business=%s trigger=%s", business_id, trigger.value)
                    return True
                logger.warning("WhatsApp failed for business=%s, falling back to email: %s", business_id, error)

            # Email fallback
            if not client.email:
                logger.info(
                    "send_notification: business %s has no email on related client, skipping trigger=%s",
                    business_id,
                    trigger.value,
                )
                return True

            notification = self.notification_repo.create(
                business_id=business_id,
                binder_id=binder_id,
                trigger=trigger,
                channel=NotificationChannel.EMAIL,
                recipient=client.email,
                content_snapshot=content,
                triggered_by=triggered_by,
                severity=severity,
            )

            success, error = self.email.send(client.email, content, subject=subject)
            if success:
                self.notification_repo.mark_sent(notification.id)
                logger.info(
                    "Notification sent | business=%s trigger=%s email=%s",
                    business_id,
                    trigger.value,
                    client.email,
                )
            else:
                self.notification_repo.mark_failed(notification.id, error or "unknown error")
                logger.error("Notification failed | business=%s trigger=%s error=%s", business_id, trigger.value, error)

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Unexpected error in send_notification | business=%s trigger=%s error=%s",
                business_id,
                trigger,
                exc,
            )

        return True

    def list_paginated(
        self, page: int = 1, page_size: int = 20, business_id: Optional[int] = None
    ) -> tuple:
        return self.notification_repo.list_paginated(page=page, page_size=page_size, business_id=business_id)

    def list_recent(self, limit: int = 20, business_id: Optional[int] = None):
        return self.notification_repo.list_recent(limit=limit, business_id=business_id)

    def count_unread(self, business_id: Optional[int] = None) -> int:
        return self.notification_repo.count_unread(business_id=business_id)

    def mark_read(self, notification_ids: list[int]) -> int:
        return self.notification_repo.mark_read(notification_ids)

    def mark_all_read(self, business_id: Optional[int] = None) -> int:
        return self.notification_repo.mark_all_read(business_id)
