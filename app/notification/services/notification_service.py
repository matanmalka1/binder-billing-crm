from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import config
from app.core.logging_config import get_logger
from app.infrastructure.notifications import EmailChannel, WhatsAppChannel
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.businesses.repositories.business_repository import BusinessRepository
from app.notification.models.notification import (
    NotificationChannel,
    NotificationSeverity,
    NotificationTrigger,
)
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.schemas.notification_schemas import NotificationResponse
from app.notification.services.messages import (
    ANNUAL_REPORT_CLIENT_REMINDER_SUBJECT,
    BINDER_READY_FOR_PICKUP_SUBJECT,
    BINDER_RECEIVED_SUBJECT,
    CONTENT_TEMPLATES,
    DEFAULT_NOTIFICATION_SUBJECT,
    FALLBACK_CLIENT_NAME,
    MANUAL_PAYMENT_REMINDER_SUBJECT,
    PICKUP_REMINDER_SUBJECT,
)

logger = get_logger(__name__)

_SUBJECTS: dict[NotificationTrigger, str] = {
    NotificationTrigger.BINDER_RECEIVED: BINDER_RECEIVED_SUBJECT,
    NotificationTrigger.BINDER_READY_FOR_PICKUP: BINDER_READY_FOR_PICKUP_SUBJECT,
    NotificationTrigger.PICKUP_REMINDER: PICKUP_REMINDER_SUBJECT,
    NotificationTrigger.ANNUAL_REPORT_CLIENT_REMINDER: ANNUAL_REPORT_CLIENT_REMINDER_SUBJECT,
    NotificationTrigger.MANUAL_PAYMENT_REMINDER: MANUAL_PAYMENT_REMINDER_SUBJECT,
}


def _enrich(
    notification: object,
    business_name_map: dict[int, str],
    client_name_map: dict[int, str],
) -> NotificationResponse:
    resp = NotificationResponse.model_validate(notification)
    resp.client_name = client_name_map.get(notification.client_record_id)
    if notification.business_id is not None:
        resp.business_name = business_name_map.get(notification.business_id)
    return resp


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.notification_repo = NotificationRepository(db)
        self.business_repo = BusinessRepository(db)
        live_delivery = config.APP_ENV in ("staging", "production")
        self.email = EmailChannel(
            enabled=config.NOTIFICATIONS_ENABLED and live_delivery,
            api_key=config.SENDGRID_API_KEY,
            api_url=config.SENDGRID_API_URL,
            from_address=config.EMAIL_FROM_ADDRESS,
            from_name=config.EMAIL_FROM_NAME,
        )
        self.whatsapp = WhatsAppChannel(
            api_key=config.WHATSAPP_API_KEY,
            api_url=config.WHATSAPP_API_URL,
            from_number=config.WHATSAPP_FROM_NUMBER,
        )

    # ── Canonical entry point ─────────────────────────────────────────────────

    def notify_client(
        self,
        client_record_id: int,
        trigger: NotificationTrigger,
        template_data: dict[str, Any] | None = None,
        business_id: Optional[int] = None,
        binder_id: Optional[int] = None,
        annual_report_id: Optional[int] = None,
        triggered_by: Optional[int] = None,
        preferred_channel: NotificationChannel = NotificationChannel.EMAIL,
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> bool:
        try:
            person = self._resolve_client_contact(client_record_id)
            if not person:
                logger.warning("notify_client: client %s not found", client_record_id)
                return False

            template = CONTENT_TEMPLATES.get(trigger.value)
            if template is None:
                logger.error("notify_client: no content template for trigger=%s", trigger)
                return False
            try:
                content = template.format(
                    name=person.full_name or FALLBACK_CLIENT_NAME,
                    **(template_data or {}),
                )
            except KeyError as exc:
                logger.error(
                    "notify_client: missing template key=%s for trigger=%s", exc, trigger
                )
                return False

            subject = _SUBJECTS.get(trigger, DEFAULT_NOTIFICATION_SUBJECT)
            log_ctx = f"client={client_record_id} trigger={trigger.value}"

            return self._deliver_to_contact(
                person=person,
                client_record_id=client_record_id,
                trigger=trigger,
                content=content,
                subject=subject,
                log_ctx=log_ctx,
                business_id=business_id,
                binder_id=binder_id,
                annual_report_id=annual_report_id,
                triggered_by=triggered_by,
                preferred_channel=preferred_channel,
                severity=severity,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Unexpected error in notify_client | client=%s trigger=%s error=%s",
                client_record_id,
                trigger,
                exc,
            )
        return False

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
        business_name_map = self._build_name_map(items)
        client_name_map = self._build_client_name_map(items)
        return [_enrich(n, business_name_map, client_name_map) for n in items], total

    def count_unread(
        self,
        client_record_id: Optional[int] = None,
        business_id: Optional[int] = None,
    ) -> int:
        return self.notification_repo.count_unread(
            client_record_id=client_record_id,
            business_id=business_id,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _deliver_to_contact(
        self,
        person: Person,
        client_record_id: int,
        trigger: NotificationTrigger,
        content: str,
        subject: str,
        log_ctx: str,
        business_id: Optional[int],
        binder_id: Optional[int],
        annual_report_id: Optional[int],
        triggered_by: Optional[int],
        preferred_channel: NotificationChannel,
        severity: NotificationSeverity,
    ) -> bool:
        phone = person.phone
        email = person.email

        if preferred_channel == NotificationChannel.WHATSAPP and self.whatsapp.enabled and phone:
            n = self.notification_repo.create(
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
            if self._deliver(n.id, NotificationChannel.WHATSAPP, phone, content, subject, log_ctx):
                return True
            logger.warning("WhatsApp failed %s, falling back to email", log_ctx)

        if not email:
            logger.info(
                "notify_client: client %s has no email, skipping trigger=%s",
                client_record_id,
                trigger.value,
            )
            return False

        n = self.notification_repo.create(
            client_record_id=client_record_id,
            business_id=business_id,
            binder_id=binder_id,
            annual_report_id=annual_report_id,
            trigger=trigger,
            channel=NotificationChannel.EMAIL,
            recipient=email,
            content_snapshot=content,
            triggered_by=triggered_by,
            severity=severity,
        )
        return self._deliver(n.id, NotificationChannel.EMAIL, email, content, subject, log_ctx)

    def _deliver(
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
                self.notification_repo.mark_sent(notification_id)
                logger.info("WhatsApp sent | %s", log_context)
                return True
            self.notification_repo.mark_failed(notification_id, err or "whatsapp failed")
            logger.warning("WhatsApp failed | %s error=%s", log_context, err)
            return False
        # channel == EMAIL
        ok, err = self.email.send(address, content, subject=subject)
        if ok:
            self.notification_repo.mark_sent(notification_id)
            logger.info("Notification sent | %s", log_context)
            return True
        self.notification_repo.mark_failed(notification_id, err or "unknown error")
        logger.error("Notification failed | %s error=%s", log_context, err)
        return False

    def _resolve_client_contact(self, client_record_id: int) -> Person | None:
        person = self.db.execute(
            select(Person)
            .select_from(ClientRecord)
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .outerjoin(
                PersonLegalEntityLink,
                (PersonLegalEntityLink.legal_entity_id == LegalEntity.id)
                & (PersonLegalEntityLink.role == PersonLegalEntityRole.OWNER),
            )
            .outerjoin(Person, Person.id == PersonLegalEntityLink.person_id)
            .where(ClientRecord.id == client_record_id)
        ).scalar()
        if person is None:
            logger.warning("ClientRecord id=%s has no linked Person", client_record_id)
        return person

    def _build_client_name_map(self, notifications: list) -> dict[int, str]:
        ids = list({n.client_record_id for n in notifications})
        if not ids:
            return {}
        rows = self.db.execute(
            select(ClientRecord.id, LegalEntity.official_name)
            .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
            .where(ClientRecord.id.in_(ids))
        ).all()
        return {row[0]: row[1] for row in rows}

    def _build_name_map(self, notifications: list) -> dict[int, str]:
        ids = [n.business_id for n in notifications if n.business_id is not None]
        if not ids:
            return {}
        businesses = self.business_repo.list_by_ids(list(set(ids)))
        return {
            b.id: getattr(b, "business_name", None) or getattr(b, "full_name", None)
            for b in businesses
        }
