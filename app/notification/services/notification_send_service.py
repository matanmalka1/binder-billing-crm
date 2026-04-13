"""NotificationSendService — low-level delivery (email + WhatsApp) and persistence."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.config import config
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.infrastructure.notifications import EmailChannel, WhatsAppChannel
from app.clients.models.client import Client
from app.businesses.models.business import Business
from app.notification.models.notification import NotificationChannel, NotificationSeverity, NotificationTrigger
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.services.constants import BULK_NOTIFY_LIMIT
from app.notification.services.messages import (
    BINDER_READY_FOR_PICKUP_SUBJECT,
    BINDER_RECEIVED_SUBJECT,
    BULK_NOTIFY_LIMIT_EXCEEDED,
    CLIENT_REMINDER_SUBJECT,
    DEFAULT_NOTIFICATION_SUBJECT,
    MANUAL_PAYMENT_REMINDER_SUBJECT,
)

logger = get_logger(__name__)

_SUBJECTS: dict[NotificationTrigger, str] = {
    NotificationTrigger.BINDER_RECEIVED: BINDER_RECEIVED_SUBJECT,
    NotificationTrigger.BINDER_READY_FOR_PICKUP: BINDER_READY_FOR_PICKUP_SUBJECT,
    NotificationTrigger.MANUAL_PAYMENT_REMINDER: MANUAL_PAYMENT_REMINDER_SUBJECT,
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
        if len(business_ids) > BULK_NOTIFY_LIMIT:
            raise AppError(
                BULK_NOTIFY_LIMIT_EXCEEDED.format(limit=BULK_NOTIFY_LIMIT),
                "NOTIFICATION.BULK_LIMIT_EXCEEDED",
            )
        results = [
            self.send_notification(
                business_id=bid, trigger=trigger, content=template,
                triggered_by=triggered_by, preferred_channel=channel.value, severity=severity,
            )
            for bid in business_ids
        ]
        sent = sum(results)
        return {"sent": sent, "failed": len(results) - sent}

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
        try:
            row = self._get_business_and_client(business_id)
            if not row:
                logger.warning("send_notification: business %s not found", business_id)
                return True
            _business, client = row

            subject = _SUBJECTS.get(trigger)
            if subject is None:
                logger.warning("No subject mapping for trigger=%s, using default", trigger)
                subject = DEFAULT_NOTIFICATION_SUBJECT

            if preferred_channel == "whatsapp" and self.whatsapp.enabled and client.phone:
                n = self.notification_repo.create(
                    client_id=client.id,        # PRIMARY anchor
                    business_id=business_id,    # optional context
                    binder_id=binder_id,
                    trigger=trigger,
                    channel=NotificationChannel.WHATSAPP,
                    recipient=client.phone,
                    content_snapshot=content,
                    triggered_by=triggered_by,
                    severity=severity,
                )
                ok, err = self.whatsapp.send(client.phone, content)
                if ok:
                    self.notification_repo.mark_sent(n.id)
                    logger.info("WhatsApp sent | business=%s trigger=%s", business_id, trigger.value)
                    return True
                self.notification_repo.mark_failed(n.id, err or "whatsapp failed")
                logger.warning("WhatsApp failed business=%s, falling back to email: %s", business_id, err)

            if not client.email:
                logger.info(
                    "send_notification: business %s has no email, skipping trigger=%s",
                    business_id, trigger.value,
                )
                return True

            n = self.notification_repo.create(
                client_id=client.id,        # PRIMARY anchor
                business_id=business_id,    # optional context
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
                self.notification_repo.mark_sent(n.id)
                logger.info("Notification sent | business=%s trigger=%s", business_id, trigger.value)
            else:
                self.notification_repo.mark_failed(n.id, error or "unknown error")
                logger.error(
                    "Notification failed | business=%s trigger=%s error=%s",
                    business_id, trigger.value, error,
                )

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Unexpected error in send_notification | business=%s trigger=%s error=%s",
                business_id, trigger, exc,
            )
        return True

    def send_client_reminder(self, client_id: int, reminder_text: str) -> bool:
        """Send reminder email directly to a client. Persists notification row. Never raises."""
        try:
            client = self.db.query(Client).filter(
                Client.id == client_id, Client.deleted_at.is_(None)
            ).first()
            if not client or not client.email:
                logger.info("send_client_reminder: client %s has no email or not found", client_id)
                return True
            n = self.notification_repo.create(
                client_id=client_id,        # PRIMARY anchor; no business_id (client-direct)
                trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
                channel=NotificationChannel.EMAIL,
                recipient=client.email,
                content_snapshot=reminder_text,
            )
            ok, err = self.email.send(client.email, reminder_text, subject=CLIENT_REMINDER_SUBJECT)
            if ok:
                self.notification_repo.mark_sent(n.id)
                logger.info("Client reminder sent | client=%s", client_id)
            else:
                self.notification_repo.mark_failed(n.id, err or "unknown error")
                logger.error("send_client_reminder failed | client=%s error=%s", client_id, err)
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error in send_client_reminder | client=%s error=%s", client_id, exc)
        return True
