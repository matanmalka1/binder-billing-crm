"""
Notification service — email-only (SendGrid).

WhatsApp is disabled. All client notifications go through email.
The service is non-blocking: it always returns True so calling code
is never interrupted by a notification failure.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.notifications import EmailChannel
from app.binders.models.binder import Binder
from app.clients.models.client import Client
from app.notification.models.notification import NotificationChannel, NotificationTrigger
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
    """Notification engine — sends emails via SendGrid."""

    def __init__(self, db: Session):
        self.db = db
        self.notification_repo = NotificationRepository(db)
        self.client_repo = ClientRepository(db)
        self.email = EmailChannel()

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

    def send_notification(
        self,
        client_id: int,
        trigger: NotificationTrigger,
        content: str,
        binder_id: Optional[int] = None,
        triggered_by: Optional[int] = None,
    ) -> bool:
        """
        Persist + send an email notification.

        Never raises — always returns True so callers are not interrupted.
        """
        try:
            client = self.client_repo.get_by_id(client_id)
            if not client:
                logger.warning("send_notification: client %s not found", client_id)
                return True

            if not client.email:
                logger.info(
                    "send_notification: client %s has no email, skipping trigger=%s",
                    client_id,
                    trigger.value,
                )
                return True

            subject = _SUBJECTS.get(trigger, "הודעה ממערכת ניהול התיקים")

            notification = self.notification_repo.create(
                client_id=client_id,
                binder_id=binder_id,
                trigger=trigger,
                channel=NotificationChannel.EMAIL,
                recipient=client.email,
                content_snapshot=content,
                triggered_by=triggered_by,
            )

            # Send
            success, error = self.email.send(client.email, content, subject=subject)

            if success:
                self.notification_repo.mark_sent(notification.id)
                logger.info(
                    "Notification sent | client=%s trigger=%s email=%s",
                    client_id,
                    trigger.value,
                    client.email,
                )
            else:
                self.notification_repo.mark_failed(notification.id, error or "unknown error")
                logger.error(
                    "Notification failed | client=%s trigger=%s error=%s",
                    client_id,
                    trigger.value,
                    error,
                )

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Unexpected error in send_notification | client=%s trigger=%s error=%s",
                client_id,
                trigger,
                exc,
            )

        return True