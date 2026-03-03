from sqlalchemy.orm import Session

_BULK_PAGE_SIZE = 1000

from app.annual_reports.models.annual_report_model import AnnualReport
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.invoice.repositories.invoice_repository import InvoiceRepository
from app.notification.repositories.notification_repository import NotificationRepository
from app.tax_deadline.models.tax_deadline import TaxDeadline
from app.timeline.repositories.timeline_repository import TimelineRepository
from app.timeline.services.timeline_event_builders import (
    binder_received_event,
    binder_returned_event,
    binder_status_change_event,
    charge_created_event,
    charge_issued_event,
    charge_paid_event,
    invoice_attached_event,
    notification_sent_event,
)
from app.timeline.services.timeline_tax_builders import (
    annual_report_status_changed_event,
    tax_deadline_due_event,
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

        notifications = self.notification_repo.list_by_client(client_id, page=1, page_size=_BULK_PAGE_SIZE)
        for notification in notifications:
            events.append(notification_sent_event(notification))

        charges = self.charge_repo.list_charges(
            client_id=client_id, page=1, page_size=_BULK_PAGE_SIZE
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

        events.extend(self._build_tax_deadline_events(client_id))
        events.extend(self._build_annual_report_events(client_id))

        events.sort(key=lambda e: e["timestamp"], reverse=True)
        total = len(events)
        offset = (page - 1) * page_size
        return events[offset : offset + page_size], total

    def _append_status_change_events(self, events: list[dict], binder) -> None:
        logs = self.status_log_repo.list_by_binder(binder.id)
        for status_log in logs:
            events.append(binder_status_change_event(binder, status_log))

    def _build_tax_deadline_events(self, client_id: int) -> list[dict]:
        deadlines = (
            self.timeline_repo.db.query(TaxDeadline)
            .filter(TaxDeadline.client_id == client_id)
            .all()
        )
        return [tax_deadline_due_event(d) for d in deadlines]

    def _build_annual_report_events(self, client_id: int) -> list[dict]:
        reports = (
            self.timeline_repo.db.query(AnnualReport)
            .filter(AnnualReport.client_id == client_id)
            .all()
        )
        return [annual_report_status_changed_event(r) for r in reports]
