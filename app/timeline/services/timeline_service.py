from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_model import AnnualReport
from app.annual_reports.models.annual_report_status_history import (
    AnnualReportStatusHistory,
)
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import (
    BinderStatusLogRepository,
)
from app.businesses.models.business import Business
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.core.exceptions import NotFoundError
from app.invoice.repositories.invoice_repository import InvoiceRepository
from app.timeline.services.timeline_binder_event_builders import (
    binder_received_event,
    binder_returned_event,
    binder_status_change_event,
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
)

# Safety ceiling for per-entity bulk fetches — per-client, not global.
_TIMELINE_BULK_LIMIT = 500


class TimelineService:
    """Unified client timeline aggregation."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.status_log_repo = BinderStatusLogRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.invoice_repo = InvoiceRepository(db)
        self.client_record_repo = ClientRecordRepository(db)

    def get_client_timeline(
        self,
        client_record_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        client_record = self.client_record_repo.get_by_id(client_record_id)
        if not client_record:
            raise NotFoundError(
                message="לקוח לא נמצא", code="TIMELINE.CLIENT_NOT_FOUND"
            )
        businesses = (
            self.db.query(Business)
            .filter(
                Business.legal_entity_id == client_record.legal_entity_id,
                Business.deleted_at.is_(None),
            )
            .all()
        )
        business_ids = [business.id for business in businesses]
        client_record_id = int(client_record.id)

        events = []

        # Bounded: _TIMELINE_BULK_LIMIT — older binders silently excluded if exceeded.
        binders = self.binder_repo.list_by_client_record(client_record_id)
        for binder in binders:
            if getattr(binder, "received_at", None) or getattr(
                binder, "period_start", None
            ):
                events.append(binder_received_event(binder))
            if binder.returned_at:
                events.append(binder_returned_event(binder))
            self._append_status_change_events(events, binder)

        # Bounded fetch — clients with more than _TIMELINE_BULK_LIMIT
        # charges will have older events silently truncated.
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

        events.extend(
            self._build_annual_report_events(
                client_record.id if client_record else None
            )
        )
        events.extend(build_client_events(self.db, client_record_id, business_ids))

        events.sort(key=lambda e: e["timestamp"], reverse=True)
        total = len(events)
        offset = (page - 1) * page_size
        return events[offset : offset + page_size], total

    @staticmethod
    def _status_str(value) -> str | None:
        """Normalise a status that may be a plain string or a BinderStatus Enum to its string value."""
        if value is None:
            return None
        return value.value if hasattr(value, "value") else str(value)

    def _append_status_change_events(self, events: list[dict], binder) -> None:
        logs = self.status_log_repo.list_by_binder(binder.id)
        for status_log in logs:
            old_status = self._status_str(getattr(status_log, "old_status", None))
            new_status = self._status_str(getattr(status_log, "new_status", None))
            if old_status == new_status:
                continue
            # Skip the synthetic none → in_office row written by the status-log
            # trigger on binder creation; it duplicates the binder_received event.
            if old_status in (None, "none") and new_status == "in_office":
                continue
            events.append(binder_status_change_event(binder, status_log))

    def _build_annual_report_events(self, client_record_id: int | None) -> list[dict]:
        query = (
            self.db.query(AnnualReport, AnnualReportStatusHistory)
            .join(
                AnnualReportStatusHistory,
                AnnualReportStatusHistory.annual_report_id == AnnualReport.id,
            )
            .filter(AnnualReport.deleted_at.is_(None))
        )
        if client_record_id is not None:
            query = query.filter(AnnualReport.client_record_id == client_record_id)
        rows = (
            query.order_by(AnnualReportStatusHistory.occurred_at.desc())
            .limit(_TIMELINE_BULK_LIMIT)
            .all()
        )
        return [
            annual_report_status_changed_event(report, history)
            for report, history in rows
        ]
