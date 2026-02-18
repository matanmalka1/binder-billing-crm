from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.notifications import EmailChannel, WhatsAppChannel
from app.binders.models.binder import Binder
from app.clients.models.client import Client
from app.notification.models.notification import NotificationChannel, NotificationTrigger
from app.clients.repositories.client_repository import ClientRepository
from app.notification.repositories.notification_repository import NotificationRepository


class NotificationService:
    """Notification engine for Sprint 4."""

    def __init__(self, db: Session):
        self.db = db
        self.notification_repo = NotificationRepository(db)
        self.client_repo = ClientRepository(db)
        self.whatsapp = WhatsAppChannel()
        self.email = EmailChannel()

    def send_notification(
        self,
        client_id: int,
        trigger: NotificationTrigger,
        content: str,
        binder_id: Optional[int] = None,
    ) -> bool:
        """
        Send notification with fallback and persistence.
        
        Non-blocking: Always returns True to avoid blocking operations.
        Persists notification regardless of send status.
        """
        client = self.client_repo.get_by_id(client_id)
        if not client:
            return True

        recipient = self._get_recipient(client)
        if not recipient:
            return True

        # Try WhatsApp first
        notification = self.notification_repo.create(
            client_id=client_id,
            binder_id=binder_id,
            trigger=trigger,
            channel=NotificationChannel.WHATSAPP,
            recipient=recipient,
            content_snapshot=content,
        )

        success, error = self.whatsapp.send(recipient, content)

        if success:
            self.notification_repo.mark_sent(notification.id)
            return True

        # WhatsApp failed, mark and try email fallback
        self.notification_repo.mark_failed(notification.id, error or "WhatsApp send failed")

        if client.email:
            email_notification = self.notification_repo.create(
                client_id=client_id,
                binder_id=binder_id,
                trigger=trigger,
                channel=NotificationChannel.EMAIL,
                recipient=client.email,
                content_snapshot=content,
            )

            email_success, email_error = self.email.send(client.email, content)

            if email_success:
                self.notification_repo.mark_sent(email_notification.id)
            else:
                self.notification_repo.mark_failed(
                    email_notification.id, email_error or "Email send failed"
                )

        return True

    def notify_binder_received(self, binder: Binder, client: Client) -> bool:
        """Send notification when binder is received."""
        content = (
            f"Binder {binder.binder_number} received on {binder.received_at}. "
            f"Expected return: {binder.expected_return_at}."
        )
        return self.send_notification(
            client_id=client.id,
            trigger=NotificationTrigger.BINDER_RECEIVED,
            content=content,
            binder_id=binder.id,
        )

    def notify_approaching_sla(self, binder: Binder, client: Client, days_remaining: int) -> bool:
        """Send notification when binder is approaching SLA threshold."""
        content = (
            f"Binder {binder.binder_number} approaching deadline. "
            f"{days_remaining} days remaining until {binder.expected_return_at}."
        )
        return self.send_notification(
            client_id=client.id,
            trigger=NotificationTrigger.BINDER_APPROACHING_SLA,
            content=content,
            binder_id=binder.id,
        )

    def notify_overdue(self, binder: Binder, client: Client, days_overdue: int) -> bool:
        """Send notification when binder is overdue."""
        content = (
            f"OVERDUE: Binder {binder.binder_number} is {days_overdue} days overdue. "
            f"Expected return was {binder.expected_return_at}."
        )
        return self.send_notification(
            client_id=client.id,
            trigger=NotificationTrigger.BINDER_OVERDUE,
            content=content,
            binder_id=binder.id,
        )

    def notify_ready_for_pickup(self, binder: Binder, client: Client) -> bool:
        """Send notification when binder is ready for pickup."""
        content = f"Binder {binder.binder_number} is ready for pickup."
        return self.send_notification(
            client_id=client.id,
            trigger=NotificationTrigger.BINDER_READY_FOR_PICKUP,
            content=content,
            binder_id=binder.id,
        )

    def notify_payment_reminder(self, client: Client, reminder_text: str) -> bool:
        """Send manual payment reminder (advisor-triggered)."""
        return self.send_notification(
            client_id=client.id,
            trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
            content=reminder_text,
        )

    @staticmethod
    def _get_recipient(client: Client) -> Optional[str]:
        """Get notification recipient (phone for WhatsApp)."""
        return client.phone
