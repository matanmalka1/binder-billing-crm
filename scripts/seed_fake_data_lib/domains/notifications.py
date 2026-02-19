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


def create_notifications(db, rng: Random, clients, binders) -> None:
    clients_by_id = {c.id: c for c in clients}
    for binder in binders:
        if rng.random() > 0.65:
            continue
        client = clients_by_id.get(binder.client_id)
        if not client:
            continue
        is_email = rng.random() < 0.35
        channel = NotificationChannel.EMAIL if is_email else NotificationChannel.WHATSAPP
        recipient = client.email if is_email else (client.phone or "0500000000")

        if binder.status == BinderStatus.OVERDUE:
            trigger = NotificationTrigger.BINDER_OVERDUE
        elif binder.status == BinderStatus.READY_FOR_PICKUP:
            trigger = NotificationTrigger.BINDER_READY_FOR_PICKUP
        else:
            trigger = rng.choice(
                [
                    NotificationTrigger.BINDER_RECEIVED,
                    NotificationTrigger.BINDER_APPROACHING_SLA,
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
            client_id=client.id,
            binder_id=binder.id,
            trigger=trigger,
            channel=channel,
            status=status,
            recipient=recipient,
            content_snapshot=f"Automated message for binder {binder.binder_number}",
            sent_at=sent_at,
            failed_at=failed_at,
            error_message=("provider_timeout" if status == NotificationStatus.FAILED else None),
            created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 60)),
        )
        db.add(notification)
    db.flush()
