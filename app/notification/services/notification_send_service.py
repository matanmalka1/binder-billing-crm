"""
NotificationSendService — low-level delivery (email + WhatsApp) and persistence.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.config import config
from app.core.exceptions import AppError
from app.core import get_logger
from app.infrastructure.notifications import EmailChannel, WhatsAppChannel
from app.clients.models.client import Client
from app.businesses.models.business import Business
from app.notification.models.notification import NotificationChannel, NotificationSeverity, NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository

logger = get_logger(__name__)

_BULK_NOTIFY_LIMIT = 500

_SUBJECTS: dict[NotificationTrigger, str] = {
    NotificationTrigger.BINDER_RECEIVED: "התיק שלך התקבל במשרד",
    NotificationTrigger.BINDER_READY_FOR_PICKUP: "התיק שלך מוכן לאיסוף",
    NotificationTrigger.MANUAL_PAYMENT_REMINDER: "תזכורת תשלום",
}


class NotificationSendService:
    """Delivery engine — email via SendGrid; WhatsApp via 360dialog when configured."""

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
        return row or None

    def bulk_notify(
        self,
        business_ids: list[int],
        template: str,
        channel: NotificationChannel = NotificationChannel.EMAIL,
        trigger: NotificationTrigger = NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        triggered_by: Optional[int] = None,
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> dict:
        if len(business_ids) > _BULK_NOTIFY_LIMIT:
            raise AppError(
                f"לא ניתן לשלוח התראות ליותר מ-{_BULK_NOTIFY_LIMIT} עסקים בבת אחת",
                "NOTIFICATION.BULK_LIMIT_EXCEEDED",
            )
        sent = 0
        failed = 0
        for business_id in business_ids:
            ok = self.send_notification(
                business_id=business_id, trigger=trigger, content=template,
                triggered_by=triggered_by, preferred_channel=channel.value, severity=severity,
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
        """Persist + send. Never raises — always returns True."""
        try:
            row = self._get_business_and_client(business_id)
            if not row:
                logger.warning("send_notification: business %s not found", business_id)
                return True
            _business, client = row

            subject = _SUBJECTS.get(trigger)
            if subject is None:
                logger.warning("No subject mapping for trigger=%s, using default", trigger)
                subject = "הודעה ממערכת ניהול התיקים"

            if preferred_channel == "whatsapp" and self.whatsapp.enabled and client.phone:
                notification = self.notification_repo.create(
                    business_id=business_id, binder_id=binder_id, trigger=trigger,
                    channel=NotificationChannel.WHATSAPP, recipient=client.phone,
                    content_snapshot=content, triggered_by=triggered_by, severity=severity,
                )
                success, error = self.whatsapp.send(client.phone, content)
                if success:
                    self.notification_repo.mark_sent(notification.id)
                    logger.info("WhatsApp sent | business=%s trigger=%s", business_id, trigger.value)
                    return True
                self.notification_repo.mark_failed(notification.id, error or "whatsapp failed")
                logger.warning("WhatsApp failed for business=%s, falling back to email: %s", business_id, error)

            if not client.email:
                logger.info(
                    "send_notification: business %s has no email, skipping trigger=%s",
                    business_id, trigger.value,
                )
                return True

            notification = self.notification_repo.create(
                business_id=business_id, binder_id=binder_id, trigger=trigger,
                channel=NotificationChannel.EMAIL, recipient=client.email,
                content_snapshot=content, triggered_by=triggered_by, severity=severity,
            )
            success, error = self.email.send(client.email, content, subject=subject)
            if success:
                self.notification_repo.mark_sent(notification.id)
                logger.info("Notification sent | business=%s trigger=%s email=%s", business_id, trigger.value, client.email)
            else:
                self.notification_repo.mark_failed(notification.id, error or "unknown error")
                logger.error("Notification failed | business=%s trigger=%s error=%s", business_id, trigger.value, error)

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Unexpected error in send_notification | business=%s trigger=%s error=%s",
                business_id, trigger, exc,
            )
        return True
