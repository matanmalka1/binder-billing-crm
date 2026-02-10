from sqlalchemy.orm import Session

from app.repositories import (
    BinderStatusLogRepository,
    ChargeRepository,
    InvoiceRepository,
    NotificationRepository,
    TimelineRepository,
)
from app.services.timeline_event_builders import (
    binder_received_event,
    binder_returned_event,
    binder_status_change_event,
    charge_created_event,
    charge_issued_event,
    charge_paid_event,
    invoice_attached_event,
    notification_sent_event,
)


class TimelineService:
    """Unified client timeline aggregation."""

    def __init__(self, db: Session):
        self.timeline_repo = TimelineRepository(db)
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
        events = []

        binders = self.timeline_repo.list_client_binders(client_id)
        for binder in binders:
            events.append(binder_received_event(binder))
            if binder.returned_at:
                events.append(binder_returned_event(binder))
            self._append_status_change_events(events, binder)

        notifications = self.notification_repo.list_by_client(client_id, page=1, page_size=1000)
        for notification in notifications:
            events.append(notification_sent_event(notification))

        charges = self.charge_repo.list_charges(
            client_id=client_id, page=1, page_size=1000
        )
        for charge in charges:
            events.append(charge_created_event(charge))
            if charge.issued_at:
                events.append(charge_issued_event(charge))
            if charge.paid_at:
                events.append(charge_paid_event(charge))
            invoice = self.invoice_repo.get_by_charge_id(charge.id)
            if invoice:
                events.append(invoice_attached_event(charge, invoice))

        events.sort(key=lambda e: e["timestamp"], reverse=True)
        total = len(events)
        offset = (page - 1) * page_size
        return events[offset : offset + page_size], total

    def _append_status_change_events(self, events: list[dict], binder) -> None:
        logs = self.status_log_repo.list_by_binder(binder.id)
        for status_log in logs:
            events.append(binder_status_change_event(binder, status_log))
