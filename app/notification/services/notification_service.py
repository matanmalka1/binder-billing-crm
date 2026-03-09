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
from app.clients.models.client import Client
from app.notification.models.notification import NotificationChannel, NotificationSeverity, NotificationTrigger
from app.clients.repositories.client_repository import ClientRepository
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
        self.client_repo = ClientRepository(db)
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

    def notify_binder_received(self, binder: Binder, client: Client) -> bool:
        content = (
            f"שלום {client.full_name},\n\n"
            f"תיק מספר {binder.binder_number} התקבל במשרד בתאריך {binder.received_at}.\n\n"
            f"בברכה"
        )
        return self.send_notification(
            client_id=client.id,
            trigger=NotificationTrigger.BINDER_RECEIVED,
            content=content,
            binder_id=binder.id,
        )

    def notify_ready_for_pickup(self, binder: Binder, client: Client) -> bool:
        content = (
            f"שלום {client.full_name},\n\n"
            f"תיק מספר {binder.binder_number} מוכן לאיסוף מהמשרד.\n\n"
            f"בברכה"
        )
        return self.send_notification(
            client_id=client.id,
            trigger=NotificationTrigger.BINDER_READY_FOR_PICKUP,
            content=content,
            binder_id=binder.id,
        )

    def notify_payment_reminder(self, client: Client, reminder_text: str, triggered_by: Optional[int] = None) -> bool:
        return self.send_notification(
            client_id=client.id,
            trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
            content=reminder_text,
            triggered_by=triggered_by,
        )

    def bulk_notify(
        self,
        client_ids: list[int],
        template: str,
        channel: str = "email",
        trigger: NotificationTrigger = NotificationTrigger.MANUAL_PAYMENT_REMINDER,
        triggered_by: Optional[int] = None,
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> dict:
        """Send a notification to a list of clients. Returns {sent, failed} counts."""
        sent = 0
        failed = 0
        for client_id in client_ids:
            ok = self.send_notification(
                client_id=client_id,
                trigger=trigger,
                content=template,
                triggered_by=triggered_by,
                preferred_channel=channel,
                severity=severity,
            )
            if ok:
                sent += 1
            else:
                failed += 1
        return {"sent": sent, "failed": failed}

    def send_notification(
        self,
        client_id: int,
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
            client = self.client_repo.get_by_id(client_id)
            if not client:
                logger.warning("send_notification: client %s not found", client_id)
                return True

            subject = _SUBJECTS.get(trigger, "הודעה ממערכת ניהול התיקים")

            # Try WhatsApp first if requested and configured
            if preferred_channel == "whatsapp" and self.whatsapp.enabled and client.phone:
                success, error = self.whatsapp.send(client.phone, content)
                if success:
                    notification = self.notification_repo.create(
                        client_id=client_id,
                        binder_id=binder_id,
                        trigger=trigger,
                        channel=NotificationChannel.WHATSAPP,
                        recipient=client.phone,
                        content_snapshot=content,
                        triggered_by=triggered_by,
                        severity=severity,
                    )
                    self.notification_repo.mark_sent(notification.id)
                    logger.info("WhatsApp sent | client=%s trigger=%s", client_id, trigger.value)
                    return True
                logger.warning("WhatsApp failed for client=%s, falling back to email: %s", client_id, error)

            # Email fallback
            if not client.email:
                logger.info("send_notification: client %s has no email, skipping trigger=%s", client_id, trigger.value)
                return True

            notification = self.notification_repo.create(
                client_id=client_id,
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
                logger.info("Notification sent | client=%s trigger=%s email=%s", client_id, trigger.value, client.email)
            else:
                self.notification_repo.mark_failed(notification.id, error or "unknown error")
                logger.error("Notification failed | client=%s trigger=%s error=%s", client_id, trigger.value, error)

        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error in send_notification | client=%s trigger=%s error=%s", client_id, trigger, exc)

        return True
