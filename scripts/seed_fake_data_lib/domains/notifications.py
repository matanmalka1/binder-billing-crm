from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from app.binders.models.binder import BinderStatus
from app.notification.models.notification import (
    Notification,
    NotificationChannel,
    NotificationSeverity,
    NotificationStatus,
    NotificationTrigger,
)
from ..demo_catalog import demo_email


def create_notifications(db, rng: Random, clients, businesses, binders, users=None) -> None:
    clients_by_id = {c.id: c for c in clients}
    businesses_by_client_id: dict[int, list] = {}
    for business in businesses:
        businesses_by_client_id.setdefault(business.client_id, []).append(business)
    created_any = False
    for binder in binders:
        if rng.random() > 0.65:
            continue
        candidate_businesses = businesses_by_client_id.get(binder.client_id, [])
        if not candidate_businesses:
            continue
        business = rng.choice(candidate_businesses)
        client = clients_by_id.get(business.client_id)
        if not client:
            continue
        is_email = rng.random() < 0.35
        channel = NotificationChannel.EMAIL if is_email else NotificationChannel.WHATSAPP
        recipient = client.email if is_email else (client.phone or "0500000000")

        if binder.status == BinderStatus.READY_FOR_PICKUP:
            trigger = NotificationTrigger.BINDER_READY_FOR_PICKUP
        else:
            trigger = rng.choice(
                [
                    NotificationTrigger.BINDER_RECEIVED,
                    NotificationTrigger.MANUAL_PAYMENT_REMINDER,
                ]
            )

        status = rng.choices(
            [NotificationStatus.SENT, NotificationStatus.PENDING, NotificationStatus.FAILED],
            weights=[75, 18, 7],
            k=1,
        )[0]
        created_at = datetime.now(UTC) - timedelta(days=rng.randint(0, 60))
        sent_at = None
        failed_at = None
        if status == NotificationStatus.SENT:
            sent_at = created_at + timedelta(days=rng.randint(0, 5), hours=rng.randint(0, 12))
            if sent_at > datetime.now(UTC):
                sent_at = datetime.now(UTC)
        elif status == NotificationStatus.FAILED:
            failed_at = created_at + timedelta(days=rng.randint(0, 3), hours=rng.randint(0, 12))
            if failed_at > datetime.now(UTC):
                failed_at = datetime.now(UTC)
        severity = rng.choice(list(NotificationSeverity))
        triggered_by = None
        if trigger == NotificationTrigger.MANUAL_PAYMENT_REMINDER and users:
            triggered_by = rng.choice(users).id

        notification = Notification(
            client_id=business.client_id,
            business_id=business.id,
            binder_id=binder.id,
            trigger=trigger,
            channel=channel,
            severity=severity,
            status=status,
            recipient=recipient,
            content_snapshot=f"הודעה אוטומטית עבור קלסר {binder.binder_number}",
            sent_at=sent_at,
            failed_at=failed_at,
            error_message=("פסק זמן מול הספק" if status == NotificationStatus.FAILED else None),
            triggered_by=triggered_by,
            created_at=created_at,
        )
        db.add(notification)
        created_any = True

    if not created_any and binders:
        fallback_binder = binders[0]
        candidate_businesses = businesses_by_client_id.get(fallback_binder.client_id, [])
        if candidate_businesses:
            business = candidate_businesses[0]
            client = clients_by_id.get(business.client_id)
            if client:
                db.add(
                    Notification(
                        client_id=business.client_id,
                        business_id=business.id,
                        binder_id=fallback_binder.id,
                        trigger=NotificationTrigger.BINDER_RECEIVED,
                        channel=NotificationChannel.EMAIL,
                        severity=NotificationSeverity.INFO,
                        status=NotificationStatus.PENDING,
                        recipient=client.email or demo_email("client", client.id),
                        content_snapshot=f"הודעה אוטומטית עבור קלסר {fallback_binder.binder_number}",
                        created_at=datetime.now(UTC),
                    )
                )

    # Guarantee full enum coverage regardless of dataset size.
    _ensure_notification_enum_coverage(db, rng, clients_by_id, businesses_by_client_id, binders)
    db.flush()


def _ensure_notification_enum_coverage(db, rng, clients_by_id, businesses_by_client_id, binders) -> None:
    """Ensure every NotificationStatus and NotificationChannel value appears at least once."""
    from sqlalchemy import select, func
    from app.database import SessionLocal

    if not binders:
        return

    binder = rng.choice(binders)
    candidate_businesses = businesses_by_client_id.get(binder.client_id, [])
    if not candidate_businesses:
        return
    business = candidate_businesses[0]
    client = clients_by_id.get(business.client_id)
    if not client:
        return

    now = datetime.now(UTC)
    for status in [NotificationStatus.PENDING, NotificationStatus.FAILED]:
        sent_at = None
        failed_at = None
        if status == NotificationStatus.FAILED:
            failed_at = now - timedelta(hours=1)
        db.add(Notification(
            client_id=business.client_id,
            business_id=business.id,
            binder_id=binder.id,
            trigger=NotificationTrigger.BINDER_RECEIVED,
            channel=NotificationChannel.WHATSAPP,
            severity=NotificationSeverity.INFO,
            status=status,
            recipient=client.phone or "0500000000",
            content_snapshot=f"הודעת כיסוי עבור קלסר {binder.binder_number}",
            sent_at=sent_at,
            failed_at=failed_at,
            error_message=("פסק זמן מול הספק" if status == NotificationStatus.FAILED else None),
            created_at=now - timedelta(hours=2),
        ))

    for channel in [NotificationChannel.EMAIL, NotificationChannel.WHATSAPP]:
        db.add(Notification(
            client_id=business.client_id,
            business_id=business.id,
            binder_id=binder.id,
            trigger=NotificationTrigger.BINDER_RECEIVED,
            channel=channel,
            severity=NotificationSeverity.INFO,
            status=NotificationStatus.SENT,
            recipient=(client.email if channel == NotificationChannel.EMAIL else (client.phone or "0500000000")),
            content_snapshot=f"הודעת כיסוי ערוץ עבור קלסר {binder.binder_number}",
            sent_at=now - timedelta(minutes=30),
            created_at=now - timedelta(hours=3),
        ))
