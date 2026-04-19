from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_model import AnnualReport
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository
from app.businesses.models.business import Business
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.models.client import Client
from app.core.exceptions import NotFoundError
from app.invoice.repositories.invoice_repository import InvoiceRepository
from app.notification.repositories.notification_repository import NotificationRepository
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.signature_requests.repositories.signature_request_repository import SignatureRequestRepository
from app.tax_deadline.models.tax_deadline import TaxDeadline
# Safety ceiling for per-entity bulk fetches — per-client, not global.
# Known architectural debt; see CLAUDE.md debt table.
_TIMELINE_BULK_LIMIT = 500

from app.timeline.services.timeline_binder_event_builders import (
    binder_received_event,
    binder_returned_event,
    binder_status_change_event,
    notification_sent_event,
)
from app.timeline.services.timeline_charge_event_builders import (
    charge_created_event,
    charge_issued_event,
    charge_paid_event,
    invoice_attached_event,
)
from app.timeline.services.timeline_client_aggregator import build_client_events
from app.timeline.services.timeline_tax_builders import (
    annual_report_status_changed_event,
    tax_deadline_due_event,
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
        self.reminder_repo = ReminderRepository(db)
        self.sig_repo = SignatureRequestRepository(db)
        self.client_record_repo = ClientRecordRepository(db)

    def get_client_timeline(
        self,
        client_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        client = (
            self.db.query(Client)
            .filter(Client.id == client_id, Client.deleted_at.is_(None))
            .first()
        )
        if not client:
            raise NotFoundError(message="לקוח לא נמצא", code="TIMELINE.CLIENT_NOT_FOUND")

        businesses = (
            self.db.query(Business)
            .filter(Business.client_id == client_id, Business.deleted_at.is_(None))
            .all()
        )
        business_ids = [business.id for business in businesses]
        client_record = self.client_record_repo.get_by_client_id(client_id)

        events = []

        # Bounded: _TIMELINE_BULK_LIMIT — older binders silently excluded if exceeded.
        binders = (
            self.binder_repo.list_by_client_record(client_record.id)
            if client_record is not None
            else self.binder_repo.list_by_client(client_id)
        )
        for binder in binders:
            events.append(binder_received_event(binder))
            if binder.returned_at:
                events.append(binder_returned_event(binder))
            self._append_status_change_events(events, binder)

        # Bounded fetch — clients with more than _TIMELINE_BULK_LIMIT
        # notifications or charges will have older events silently truncated.
        for business_id in business_ids:
            notifications = self.notification_repo.list_by_business(
                business_id, page=1, page_size=_TIMELINE_BULK_LIMIT
            )
            for notification in notifications:
                events.append(notification_sent_event(notification))

        charges = self.charge_repo.list_charges(
            business_ids=business_ids, page=1, page_size=_TIMELINE_BULK_LIMIT
        )
        invoice_map = {
            inv.charge_id: inv
            for inv in self.invoice_repo.list_by_charge_ids([c.id for c in charges])
        }
        for charge in charges:
            events.append(charge_created_event(charge))
            if charge.issued_at:
                events.append(charge_issued_event(charge))
            if charge.paid_at:
                events.append(charge_paid_event(charge))
            invoice = invoice_map.get(charge.id)
            if invoice:
                events.append(invoice_attached_event(charge, invoice))

        events.extend(self._build_tax_deadline_events(client_id, business_ids, client_record.id if client_record else None))
        events.extend(self._build_annual_report_events(client_id, client_record.id if client_record else None))
        events.extend(
            build_client_events(
                self.db, client_id, business_ids, self.reminder_repo, self.sig_repo
            )
        )

        events.sort(key=lambda e: e["timestamp"], reverse=True)
        total = len(events)
        offset = (page - 1) * page_size
        return events[offset : offset + page_size], total

    def _append_status_change_events(self, events: list[dict], binder) -> None:
        logs = self.status_log_repo.list_by_binder(binder.id)
        for status_log in logs:
            events.append(binder_status_change_event(binder, status_log))

    def _build_tax_deadline_events(self, client_id: int, business_ids: list[int], client_record_id: int | None) -> list[dict]:
        # Tax deadlines are per-client and naturally bounded (months × years).
        query = self.db.query(TaxDeadline).filter(TaxDeadline.deleted_at.is_(None))
        if client_record_id is not None:
            query = query.filter(TaxDeadline.client_record_id == client_record_id)
        else:
            query = query.filter(TaxDeadline.client_id == client_id)
        deadlines = query.limit(_TIMELINE_BULK_LIMIT).all()
        return [tax_deadline_due_event(d) for d in deadlines]

    def _build_annual_report_events(self, client_id: int, client_record_id: int | None) -> list[dict]:
        # Annual reports are bounded by tax years — limit is a safety net only.
        query = self.db.query(AnnualReport).filter(AnnualReport.deleted_at.is_(None))
        if client_record_id is not None:
            query = query.filter(AnnualReport.client_record_id == client_record_id)
        else:
            query = query.filter(AnnualReport.client_id == client_id)
        reports = query.limit(_TIMELINE_BULK_LIMIT).all()
        return [annual_report_status_changed_event(r) for r in reports]
