from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.core.logging_config import get_logger
from app.infrastructure.notifications import EmailChannel, WhatsAppChannel
from app.notification.models.notification import (
    NotificationChannel,
    NotificationSeverity,
    NotificationStatus,
    NotificationTrigger,
)
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.schemas.notification_schemas import (
    ManualSendRequest,
    NotificationResponse,
    NotificationSummaryResponse,
)
from app.notification.services.messages import FALLBACK_CLIENT_NAME
from app.notification.services.notification_delivery_service import (
    NotificationDeliveryService,
)
from app.notification.services.notification_template_renderer import (
    NotificationTemplateRenderer,
)

logger = get_logger(__name__)


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
        live_delivery = settings.APP_ENV in ("staging", "production")
        self.email = EmailChannel(
            enabled=settings.NOTIFICATIONS_ENABLED and live_delivery,
            api_key=settings.BREVO_API_KEY,
            api_url=settings.BREVO_API_URL,
            from_address=settings.EMAIL_FROM_ADDRESS,
            from_name=settings.EMAIL_FROM_NAME,
        )
        self.whatsapp = WhatsAppChannel(
            api_key=settings.WHATSAPP_API_KEY,
            api_url=settings.WHATSAPP_API_URL,
            from_number=settings.WHATSAPP_FROM_NUMBER,
        )
        self._renderer = NotificationTemplateRenderer()
        self._delivery = NotificationDeliveryService(
            repo=self.notification_repo,
            email=self.email,
            whatsapp=self.whatsapp,
        )

    # ── Canonical entry point ─────────────────────────────────────────────────

    def notify_client(
        self,
        client_record_id: int,
        trigger: NotificationTrigger,
        template_data: dict[str, Any] | None = None,
        business_id: int | None = None,
        binder_id: int | None = None,
        annual_report_id: int | None = None,
        triggered_by: int | None = None,
        preferred_channel: NotificationChannel = NotificationChannel.EMAIL,
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> bool:
        client_record = self.db.get(ClientRecord, client_record_id)
        if client_record is None:
            raise NotFoundError("הלקוח לא נמצא", "CLIENT.NOT_FOUND")

        if business_id is not None:
            business = self.business_repo.get_by_id(business_id)
            if business is None:
                raise AppError("העסק לא נמצא", "NOTIFICATION.BUSINESS_NOT_FOUND")
            if business.legal_entity_id != client_record.legal_entity_id:
                raise AppError("העסק אינו שייך ללקוח שצוין", "NOTIFICATION.BUSINESS_MISMATCH")

        person = self._resolve_client_contact(client_record_id)
        person_name = person.full_name if person else FALLBACK_CLIENT_NAME

        content, subject = self._renderer.render(
            trigger=trigger,
            template_data=template_data or {},
            person_name=person_name,
        )

        if not person:
            logger.warning("notify_client: client %s has no linked person", client_record_id)
            return False

        log_ctx = f"client={client_record_id} trigger={trigger.value}"
        return self._delivery.deliver(
            person=person,
            client_record_id=client_record_id,
            trigger=trigger,
            content=content,
            subject=subject,
            preferred_channel=preferred_channel,
            severity=severity,
            business_id=business_id,
            binder_id=binder_id,
            annual_report_id=annual_report_id,
            triggered_by=triggered_by,
            log_ctx=log_ctx,
        )

    # ── Manual send ───────────────────────────────────────────────────────────

    def send_manual(self, request: ManualSendRequest, triggered_by: int) -> bool:
        return self.notify_client(
            client_record_id=request.client_record_id,
            trigger=NotificationTrigger.MANUAL_PAYMENT_REMINDER,
            template_data={"message": request.message},
            business_id=request.business_id,
            triggered_by=triggered_by,
            preferred_channel=request.preferred_channel,
        )

    # ── Read / list ───────────────────────────────────────────────────────────

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        client_record_id: int | None = None,
        business_id: int | None = None,
        status: NotificationStatus | None = None,
        trigger: NotificationTrigger | None = None,
        channel: NotificationChannel | None = None,
    ) -> tuple:
        items, total = self.notification_repo.list_paginated(
            page=page,
            page_size=page_size,
            client_record_id=client_record_id,
            business_id=business_id,
            status=status,
            trigger=trigger,
            channel=channel,
        )
        business_name_map = self._build_name_map(items)
        client_name_map = self._build_client_name_map(items)
        return [_enrich(n, business_name_map, client_name_map) for n in items], total

    def get_summary(
        self,
        client_record_id: int | None = None,
        business_id: int | None = None,
    ) -> NotificationSummaryResponse:
        counts = self.notification_repo.count_by_status(
            client_record_id=client_record_id,
            business_id=business_id,
        )
        return NotificationSummaryResponse(**counts)

    # ── Internal helpers ──────────────────────────────────────────────────────

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
