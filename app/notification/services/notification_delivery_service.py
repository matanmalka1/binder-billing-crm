from __future__ import annotations

from typing import Optional

from app.core.logging_config import get_logger
from app.clients.models.person import Person
from app.infrastructure.notifications import EmailChannel, WhatsAppChannel
from app.notification.models.notification import (
    NotificationChannel,
    NotificationSeverity,
    NotificationTrigger,
)
from app.notification.repositories.notification_repository import NotificationRepository

logger = get_logger(__name__)


class NotificationDeliveryService:
    def __init__(
        self,
        repo: NotificationRepository,
        email: EmailChannel,
        whatsapp: WhatsAppChannel,
    ):
        self.repo = repo
        self.email = email
        self.whatsapp = whatsapp

    def deliver(
        self,
        person: Person,
        client_record_id: int,
        trigger: NotificationTrigger,
        content: str,
        subject: str,
        preferred_channel: NotificationChannel,
        severity: NotificationSeverity,
        business_id: Optional[int],
        binder_id: Optional[int],
        annual_report_id: Optional[int],
        triggered_by: Optional[int],
        log_ctx: str,
    ) -> bool:
        """WhatsApp → email fallback. Persists attempt records."""
        phone = person.phone
        email_addr = person.email

        if (
            preferred_channel == NotificationChannel.WHATSAPP
            and self.whatsapp.enabled
            and phone
        ):
            n = self.repo.create(
                client_record_id=client_record_id,
                business_id=business_id,
                binder_id=binder_id,
                annual_report_id=annual_report_id,
                trigger=trigger,
                channel=NotificationChannel.WHATSAPP,
                recipient=phone,
                content_snapshot=content,
                triggered_by=triggered_by,
                severity=severity,
            )
            if self._send_to_channel(
                n.id, NotificationChannel.WHATSAPP, phone, content, subject, log_ctx
            ):
                return True
            logger.warning("WhatsApp failed %s, falling back to email", log_ctx)

        if not email_addr:
            logger.info(
                "notify_client: client %s has no email, skipping trigger=%s",
                client_record_id,
                trigger.value,
            )
            return False

        n = self.repo.create(
            client_record_id=client_record_id,
            business_id=business_id,
            binder_id=binder_id,
            annual_report_id=annual_report_id,
            trigger=trigger,
            channel=NotificationChannel.EMAIL,
            recipient=email_addr,
            content_snapshot=content,
            triggered_by=triggered_by,
            severity=severity,
        )
        return self._send_to_channel(
            n.id, NotificationChannel.EMAIL, email_addr, content, subject, log_ctx
        )

    def _send_to_channel(
        self,
        notification_id: int,
        channel: NotificationChannel,
        address: str,
        content: str,
        subject: str,
        log_context: str,
    ) -> bool:
        if channel == NotificationChannel.WHATSAPP:
            ok, err = self.whatsapp.send(address, content)
            if ok:
                self.repo.mark_sent(notification_id)
                logger.info("WhatsApp sent | %s", log_context)
                return True
            self.repo.mark_failed(notification_id, err or "whatsapp failed")
            logger.warning("WhatsApp failed | %s error=%s", log_context, err)
            return False
        # channel == EMAIL
        ok, err = self.email.send(address, content, subject=subject)
        if ok:
            self.repo.mark_sent(notification_id)
            logger.info("Notification sent | %s", log_context)
            return True
        self.repo.mark_failed(notification_id, err or "unknown error")
        logger.error("Notification failed | %s error=%s", log_context, err)
        return False
