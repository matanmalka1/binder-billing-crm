"""NotificationSendService — low-level delivery (email + WhatsApp) and persistence."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.config import config
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.infrastructure.notifications import EmailChannel, WhatsAppChannel
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import PersonLegalEntityLink, PersonLegalEntityRole
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

    def _get_business_and_client(
        self, business_id: int
    ) -> tuple[Business, Person | None] | None:
        row = (
            self.db.query(Business, Person)
            .outerjoin(
                LegalEntity,
                LegalEntity.id == Business.legal_entity_id,
            )
            .outerjoin(
                PersonLegalEntityLink,
                (PersonLegalEntityLink.legal_entity_id == LegalEntity.id)
                & (PersonLegalEntityLink.role == PersonLegalEntityRole.OWNER),
            )
            .outerjoin(Person, Person.id == PersonLegalEntityLink.person_id)
            .filter(Business.id == business_id)
            .first()
        )
        if not row:
            return None
        business, person = row
        if person is None:
            logger.warning("LegalEntity for business_id=%s has no linked Person", business_id)
        return business, person

    def _get_client(self, client_record_id: int) -> Person | None:
        person = (
            self.db.query(Person)
            .select_from(ClientRecord)
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .outerjoin(
                PersonLegalEntityLink,
                (PersonLegalEntityLink.legal_entity_id == LegalEntity.id)
                & (PersonLegalEntityLink.role == PersonLegalEntityRole.OWNER),
            )
            .outerjoin(Person, Person.id == PersonLegalEntityLink.person_id)
            .filter(ClientRecord.id == client_record_id)
            .first()
        )
        if person is None:
            logger.warning("ClientRecord id=%s has no linked Person", client_record_id)
        return person

    def _get_client_record_id_for_business(self, business: Business) -> int | None:
        if business.legal_entity_id is None:
            return None
        row = (
            self.db.query(ClientRecord.id)
            .filter(
                ClientRecord.legal_entity_id == business.legal_entity_id,
                ClientRecord.deleted_at.is_(None),
            )
            .first()
        )
        return row[0] if row else None

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
                return False
            business, person = row

            subject = _SUBJECTS.get(trigger)
            if subject is None:
                logger.warning("No subject mapping for trigger=%s, using default", trigger)
                subject = DEFAULT_NOTIFICATION_SUBJECT

            phone = person.phone if person else None
            email = person.email if person else None
            cr_id = self._get_client_record_id_for_business(business)

            if preferred_channel == "whatsapp" and self.whatsapp.enabled and phone:
                n = self.notification_repo.create(
                    client_record_id=cr_id,
                    business_id=business_id,
                    binder_id=binder_id,
                    trigger=trigger,
                    channel=NotificationChannel.WHATSAPP,
                    recipient=phone,
                    content_snapshot=content,
                    triggered_by=triggered_by,
                    severity=severity,
                )
                ok, err = self.whatsapp.send(phone, content)
                if ok:
                    self.notification_repo.mark_sent(n.id)
                    logger.info("WhatsApp sent | business=%s trigger=%s", business_id, trigger.value)
                    return True
                self.notification_repo.mark_failed(n.id, err or "whatsapp failed")
                logger.warning("WhatsApp failed business=%s, falling back to email: %s", business_id, err)

            if not email:
                logger.info(
                    "send_notification: business %s has no email, skipping trigger=%s",
                    business_id, trigger.value,
                )
                return False

            n = self.notification_repo.create(
                client_record_id=cr_id,
                business_id=business_id,
                binder_id=binder_id,
                trigger=trigger,
                channel=NotificationChannel.EMAIL,
                recipient=email,
                content_snapshot=content,
                triggered_by=triggered_by,
                severity=severity,
            )
            success, error = self.email.send(email, content, subject=subject)
            if success:
                self.notification_repo.mark_sent(n.id)
                logger.info("Notification sent | business=%s trigger=%s", business_id, trigger.value)
                return True
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
        return False

    def send_client_notification(
        self,
        client_record_id: int,
        trigger: NotificationTrigger,
        content: str,
        binder_id: Optional[int] = None,
        triggered_by: Optional[int] = None,
        preferred_channel: str = "email",
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> bool:
        try:
            person = self._get_client(client_record_id)
            if not person:
                logger.warning("send_client_notification: client %s not found", client_record_id)
                return False

            subject = _SUBJECTS.get(trigger)
            if subject is None:
                logger.warning("No subject mapping for trigger=%s, using default", trigger)
                subject = DEFAULT_NOTIFICATION_SUBJECT

            phone = person.phone if person else None
            email = person.email if person else None

            if preferred_channel == "whatsapp" and self.whatsapp.enabled and phone:
                n = self.notification_repo.create(
                    client_record_id=client_record_id,
                    binder_id=binder_id,
                    trigger=trigger,
                    channel=NotificationChannel.WHATSAPP,
                    recipient=phone,
                    content_snapshot=content,
                    triggered_by=triggered_by,
                    severity=severity,
                )
                ok, err = self.whatsapp.send(phone, content)
                if ok:
                    self.notification_repo.mark_sent(n.id)
                    logger.info("Client notification sent via WhatsApp | client=%s trigger=%s", client_record_id, trigger.value)
                    return True
                self.notification_repo.mark_failed(n.id, err or "whatsapp failed")
                logger.warning("WhatsApp failed client=%s, falling back to email: %s", client_record_id, err)

            if not email:
                logger.info(
                    "send_client_notification: client %s has no email, skipping trigger=%s",
                    client_record_id, trigger.value,
                )
                return False

            n = self.notification_repo.create(
                client_record_id=client_record_id,
                binder_id=binder_id,
                trigger=trigger,
                channel=NotificationChannel.EMAIL,
                recipient=email,
                content_snapshot=content,
                triggered_by=triggered_by,
                severity=severity,
            )
            success, error = self.email.send(email, content, subject=subject)
            if success:
                self.notification_repo.mark_sent(n.id)
                logger.info("Client notification sent | client=%s trigger=%s", client_record_id, trigger.value)
                return True
            self.notification_repo.mark_failed(n.id, error or "unknown error")
            logger.error(
                "Client notification failed | client=%s trigger=%s error=%s",
                client_record_id, trigger.value, error,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Unexpected error in send_client_notification | client=%s trigger=%s error=%s",
                client_record_id, trigger, exc,
            )
        return False

    def send_client_reminder(self, client_record_id: int, reminder_text: str) -> bool:
        """Send reminder email directly to a client resolved via ClientRecord → LegalEntity → Person."""
        try:
            person = self._get_client(client_record_id)
            if person is None:
                logger.warning("send_client_reminder: client_record %s has no linked Person", client_record_id)
                return False
            email = person.email
            if not email:
                logger.info("send_client_reminder: client %s has no email or not found", client_record_id)
                return False
            n = self.notification_repo.create(
                client_record_id=client_record_id,
                trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
                channel=NotificationChannel.EMAIL,
                recipient=email,
                content_snapshot=reminder_text,
            )
            ok, err = self.email.send(email, reminder_text, subject=CLIENT_REMINDER_SUBJECT)
            if ok:
                self.notification_repo.mark_sent(n.id)
                logger.info("Client reminder sent | client=%s", client_record_id)
                return True
            self.notification_repo.mark_failed(n.id, err or "unknown error")
            logger.error("send_client_reminder failed | client=%s error=%s", client_record_id, err)
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error in send_client_reminder | client=%s error=%s", client_record_id, exc)
        return False

    def send_client_record_reminder(self, client_record_id: int, reminder_text: str) -> bool:
        """Send reminder to a client resolved from client_record_id via LegalEntity → Person."""
        try:
            person = self._get_client(client_record_id)
            if person is None:
                logger.warning("send_client_record_reminder: client_record %s has no linked Person", client_record_id)
                return False
            email = person.email
            if not email:
                logger.info("send_client_record_reminder: client_record %s has no email", client_record_id)
                return False
            n = self.notification_repo.create(
                client_record_id=client_record_id,
                trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
                channel=NotificationChannel.EMAIL,
                recipient=email,
                content_snapshot=reminder_text,
            )
            ok, err = self.email.send(email, reminder_text, subject=CLIENT_REMINDER_SUBJECT)
            if ok:
                self.notification_repo.mark_sent(n.id)
                logger.info("Client record reminder sent | client_record=%s", client_record_id)
                return True
            self.notification_repo.mark_failed(n.id, err or "unknown error")
            logger.error("send_client_record_reminder failed | client_record=%s error=%s", client_record_id, err)
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error in send_client_record_reminder | client_record=%s error=%s", client_record_id, exc)
        return False
