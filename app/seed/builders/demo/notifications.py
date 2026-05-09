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

from ...data.demo_catalog import demo_email


def create_notifications(
    db, rng: Random, clients, businesses, binders, users=None
) -> None:
    clients_by_id = {c.id: c for c in clients}
    businesses_by_client: dict[int, list] = {}
    for business in businesses:
        businesses_by_client.setdefault(business.client_id, []).append(business)

    for binder in binders:
        if rng.random() > 0.65:
            continue
        candidate_businesses = businesses_by_client.get(binder.client_id, [])
        if not candidate_businesses:
            continue
        business = rng.choice(candidate_businesses)
        client = clients_by_id.get(business.client_id)
        if not client:
            continue

        is_email = rng.random() < 0.35
        channel = (
            NotificationChannel.EMAIL if is_email else NotificationChannel.WHATSAPP
        )
        recipient = (
            getattr(client, "email", None)
            if is_email
            else (getattr(client, "phone", None) or "0500000000")
        )
        if not recipient:
            recipient = demo_email("client", client.id)

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
            [
                NotificationStatus.SENT,
                NotificationStatus.PENDING,
                NotificationStatus.FAILED,
            ],
            weights=[75, 18, 7],
            k=1,
        )[0]
        created_at = datetime.now(UTC) - timedelta(days=rng.randint(0, 60))
        sent_at = None
        failed_at = None
        if status == NotificationStatus.SENT:
            sent_at = min(
                datetime.now(UTC),
                created_at
                + timedelta(days=rng.randint(0, 5), hours=rng.randint(0, 12)),
            )
        elif status == NotificationStatus.FAILED:
            failed_at = min(
                datetime.now(UTC),
                created_at
                + timedelta(days=rng.randint(0, 3), hours=rng.randint(0, 12)),
            )

        triggered_by = None
        if trigger == NotificationTrigger.MANUAL_PAYMENT_REMINDER and users:
            triggered_by = rng.choice(users).id

        notification = Notification(
            client_record_id=business.client_id,
            business_id=business.id,
            binder_id=binder.id,
            trigger=trigger,
            channel=channel,
            severity=rng.choice(list(NotificationSeverity)),
            status=status,
            recipient=recipient,
            content_snapshot=f"הודעה אוטומטית עבור קלסר {binder.binder_number}",
            sent_at=sent_at,
            failed_at=failed_at,
            error_message="פסק זמן מול הספק"
            if status == NotificationStatus.FAILED
            else None,
            triggered_by=triggered_by,
            created_at=created_at,
        )
        notification.client_id = business.client_id  # type: ignore[attr-defined]
        db.add(notification)

    db.flush()
