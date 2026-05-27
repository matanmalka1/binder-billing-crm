from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from app.clients.models.client_record import ClientRecord
from app.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging_config import get_logger
from app.infrastructure.notifications import EmailChannel, WhatsAppChannel
from app.notification.models.notification import (
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.schemas.notification_schemas import NotificationResult
from app.notification.services.constants import NOTIFICATION_IDEMPOTENCY_TTL_HOURS
from app.notification.services.notification_context_resolver import (
    NotificationContextResolver,
)
from app.notification.services.notification_delivery_service import (
    NotificationDeliveryService,
)
from app.notification.services.notification_policy_service import (
    NotificationPolicyService,
)
from app.notification.services.notification_template_renderer import (
    NotificationTemplateRenderer,
)

logger = get_logger(__name__)


def _hash_auto(trigger: str, client_record_id: int, idempotency_key: str) -> str:
    payload = json.dumps(
        {"trigger": trigger, "cr": client_record_id, "key": idempotency_key},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class NotificationAutoSendService:
    """
    Internal send path — not exposed via HTTP.

    Used only by BinderLifecycleService (Phase 2) for binder_ready_for_handover.
    Renders template server-side, runs policy, resolves contact, delivers.
    idempotency_key is required.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = NotificationRepository(db)
        self.policy = NotificationPolicyService()
        self.renderer = NotificationTemplateRenderer()
        self.resolver = NotificationContextResolver(db)
        live = settings.APP_ENV in ("staging", "production")
        self._email = EmailChannel(
            enabled=settings.NOTIFICATIONS_ENABLED and live,
            api_key=settings.BREVO_API_KEY,
            api_url=settings.BREVO_API_URL,
            from_address=settings.EMAIL_FROM_ADDRESS,
            from_name=settings.EMAIL_FROM_NAME,
        )
        self._whatsapp = WhatsAppChannel(
            api_key=settings.WHATSAPP_API_KEY,
            api_url=settings.WHATSAPP_API_URL,
            from_number=settings.WHATSAPP_FROM_NUMBER,
        )
        self._delivery = NotificationDeliveryService()

    def auto_send(
        self,
        trigger: NotificationTrigger,
        client_record_id: int,
        idempotency_key: str,
        entity_id: int | None = None,
        business_id: int | None = None,
        binder_id: int | None = None,
        annual_report_id: int | None = None,
        signature_request_id: int | None = None,
        entity_type: str | None = None,
        triggered_by: int | None = None,
    ) -> NotificationResult:
        req_hash = _hash_auto(trigger.value, client_record_id, idempotency_key)

        existing = self.repo.find_by_idempotency_key(
            idempotency_key,
            ttl_hours=NOTIFICATION_IDEMPOTENCY_TTL_HOURS,
        )
        if existing is not None:
            if existing.request_hash != req_hash:
                logger.warning(
                    "auto_send: idempotency key reused with different payload key=%s",
                    idempotency_key,
                )
            return NotificationResult(
                status=existing.status.value,  # type: ignore[arg-type]
                notification_id=existing.id,
                reason="כבר נשלח (idempotency)",
            )

        client_record = self.db.get(ClientRecord, client_record_id)
        if client_record is None:
            raise NotFoundError("הלקוח לא נמצא", "CLIENT.NOT_FOUND")

        policy = self.policy.can_send(client_record, trigger)
        if policy.blocked:
            return NotificationResult(status="blocked", reason=policy.reason)

        ctx = self.resolver.resolve(
            trigger=trigger,
            client_record_id=client_record_id,
            entity_id=entity_id,
            business_id=business_id,
            triggered_by_user_id=triggered_by,
        )
        person_name = self.resolver.resolve_client_name(client_record_id)

        body, subject = self.renderer.render(trigger, ctx, person_name)

        person = self.resolver.resolve_person(client_record_id)
        recipient = person.email if person else None
        phone = person.phone if person else None

        if not recipient:
            n = self.repo.create(
                client_record_id=client_record_id,
                trigger=trigger,
                channel=NotificationChannel.EMAIL,
                recipient=None,
                content_snapshot=body,
                subject_snapshot=subject,
                business_id=business_id,
                binder_id=binder_id,
                annual_report_id=annual_report_id,
                signature_request_id=signature_request_id,
                entity_type=entity_type,
                entity_id=entity_id,
                triggered_by=triggered_by,
                idempotency_key=idempotency_key,
                request_hash=req_hash,
                status=NotificationStatus.SKIPPED,
            )
            logger.info(
                "auto_send skipped: no email | client=%s trigger=%s id=%s",
                client_record_id,
                trigger.value,
                n.id,
            )
            return NotificationResult(
                status="skipped",
                notification_id=n.id,
                reason="לא נמצאה כתובת אימייל עבור הלקוח",
            )

        if phone and self._whatsapp.enabled:
            channel = NotificationChannel.WHATSAPP
            delivery_recipient = phone
        else:
            channel = NotificationChannel.EMAIL
            delivery_recipient = recipient

        n = self.repo.create(
            client_record_id=client_record_id,
            trigger=trigger,
            channel=channel,
            recipient=delivery_recipient,
            content_snapshot=body,
            subject_snapshot=subject,
            business_id=business_id,
            binder_id=binder_id,
            annual_report_id=annual_report_id,
            signature_request_id=signature_request_id,
            entity_type=entity_type,
            entity_id=entity_id,
            triggered_by=triggered_by,
            idempotency_key=idempotency_key,
            request_hash=req_hash,
            status=NotificationStatus.PENDING,
        )

        ok, err = self._delivery.send(
            channel=channel,
            recipient=delivery_recipient,
            subject=subject,
            body=body,
            email_channel=self._email,
            whatsapp_channel=self._whatsapp,
        )

        if ok:
            self.repo.mark_sent(n.id)
            return NotificationResult(status="sent", notification_id=n.id)

        if channel == NotificationChannel.WHATSAPP and recipient:
            ok_email, err_email = self._delivery.send(
                channel=NotificationChannel.EMAIL,
                recipient=recipient,
                subject=subject,
                body=body,
                email_channel=self._email,
                whatsapp_channel=self._whatsapp,
            )
            if ok_email:
                n.channel = NotificationChannel.EMAIL
                n.recipient = recipient
                self.repo.mark_sent(n.id)
                return NotificationResult(status="sent", notification_id=n.id)
            self.repo.mark_failed(n.id, err_email or "email fallback failed")
            return NotificationResult(
                status="failed", notification_id=n.id, reason=err_email
            )

        self.repo.mark_failed(n.id, err or "delivery failed")
        return NotificationResult(status="failed", notification_id=n.id, reason=err)
