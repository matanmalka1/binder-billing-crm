from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from app.binders.models.binder import BinderStatus
from app.notification.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationTrigger,
)


def create_notifications(db, rng: Random, clients, businesses, binders) -> None:
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
        sent_at = datetime.now(UTC) - timedelta(days=rng.randint(0, 50)) if status == NotificationStatus.SENT else None
        failed_at = datetime.now(UTC) - timedelta(days=rng.randint(0, 50)) if status == NotificationStatus.FAILED else None

        notification = Notification(
            business_id=business.id,
            binder_id=binder.id,
            trigger=trigger,
            channel=channel,
            status=status,
            recipient=recipient,
            content_snapshot=f"הודעה אוטומטית עבור קלסר {binder.binder_number}",
            sent_at=sent_at,
            failed_at=failed_at,
            error_message=("פסק זמן מול הספק" if status == NotificationStatus.FAILED else None),
            created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 60)),
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
                        business_id=business.id,
                        binder_id=fallback_binder.id,
                        trigger=NotificationTrigger.BINDER_RECEIVED,
                        channel=NotificationChannel.EMAIL,
                        status=NotificationStatus.PENDING,
                        recipient=client.email or "client@example.com",
                        content_snapshot=f"הודעה אוטומטית עבור קלסר {fallback_binder.binder_number}",
                        created_at=datetime.now(UTC),
                    )
                )
    db.flush()
