from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories import (
    BinderRepository,
    BinderStatusLogRepository,
    ChargeRepository,
    InvoiceRepository,
    NotificationRepository,
)


class TimelineService:
    """Unified client timeline aggregation."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.status_log_repo = BinderStatusLogRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.invoice_repo = InvoiceRepository(db)
        self.notification_repo = NotificationRepository(db)

    def get_client_timeline(
        self,
        client_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        """
        Aggregate all client events into chronological timeline.
        
        Sources:
        - Binder intake
        - Binder status changes
        - Notifications
        - Charges
        - Invoices
        """
        events = []

        # Binder events
        binders = self.binder_repo.list_active(client_id=client_id)
        for binder in binders:
            # Intake event
            events.append({
                "event_type": "binder_received",
                "timestamp": datetime.combine(binder.received_at, datetime.min.time()),
                "binder_id": binder.id,
                "charge_id": None,
                "description": f"Binder {binder.binder_number} received",
                "metadata": {"binder_number": binder.binder_number},
            })

            # Status change events
            logs = self.status_log_repo.list_by_binder(binder.id)
            for log in logs:
                events.append({
                    "event_type": "binder_status_change",
                    "timestamp": log.changed_at,
                    "binder_id": binder.id,
                    "charge_id": None,
                    "description": f"Binder {binder.binder_number}: {log.old_status} → {log.new_status}",
                    "metadata": {
                        "old_status": log.old_status,
                        "new_status": log.new_status,
                    },
                })

        # Notification events
        notifications = self.notification_repo.list_by_client(
            client_id, page=1, page_size=1000
        )
        for notif in notifications:
            events.append({
                "event_type": "notification_sent",
                "timestamp": notif.created_at,
                "binder_id": notif.binder_id,
                "charge_id": None,
                "description": f"Notification: {notif.trigger.value}",
                "metadata": {
                    "trigger": notif.trigger.value,
                    "channel": notif.channel.value,
                },
            })

        # Charge events
        charges = self.charge_repo.list_charges(
            client_id=client_id, page=1, page_size=1000
        )
        for charge in charges:
            events.append({
                "event_type": "charge_created",
                "timestamp": charge.created_at,
                "binder_id": None,
                "charge_id": charge.id,
                "description": f"Charge created: {charge.charge_type.value}",
                "metadata": {
                    "amount": float(charge.amount),
                    "status": charge.status.value,
                },
            })

        # Sort chronologically (descending)
        events.sort(key=lambda e: e["timestamp"], reverse=True)

        total = len(events)
        offset = (page - 1) * page_size
        return events[offset : offset + page_size], total