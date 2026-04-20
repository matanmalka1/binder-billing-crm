from __future__ import annotations

from sqlalchemy.orm import Session

from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.annual_reports.repositories.report_repository import AnnualReportReportRepository as AnnualReportRepository
from app.binders.repositories.binder_repository import BinderRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.client_repository import ClientRepository
from app.reminders.repositories.reminder_repository import ReminderRepository
from app.reminders.services import factory as reminder_factory
from app.reminders.services import reminder_queries, status_changes
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


class ReminderService:
    """Facade delegating reminder flows to focused modules."""

    def __init__(self, db: Session):
        self.db = db
        self.reminder_repo = ReminderRepository(db)
        self.business_repo = BusinessRepository(db)
        self.client_repo = ClientRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.binder_repo = BinderRepository(db)
        self.tax_deadline_repo = TaxDeadlineRepository(db)
        self.annual_report_repo = AnnualReportRepository(db)
        self.advance_payment_repo = AdvancePaymentRepository(db)

    # ── Creation flows ────────────────────────────────────────────────────────

    def create_tax_deadline_reminder(self, **kwargs):
        return reminder_factory.create_tax_deadline_reminder(
            self.reminder_repo, self.client_repo, self.tax_deadline_repo, **kwargs
        )

    def create_vat_filing_reminder(self, **kwargs):
        return reminder_factory.create_vat_filing_reminder(
            self.reminder_repo, self.tax_deadline_repo, **kwargs
        )

    def create_idle_binder_reminder(self, **kwargs):
        return reminder_factory.create_idle_binder_reminder(
            self.reminder_repo, self.binder_repo, **kwargs
        )

    def create_annual_report_deadline_reminder(self, **kwargs):
        return reminder_factory.create_annual_report_deadline_reminder(
            self.reminder_repo, self.annual_report_repo, **kwargs
        )

    def create_unpaid_charge_reminder(self, *, client_record_id: int, **kwargs):
        if client_record_id is None:
            raise ValueError("client_record_id required")
        return reminder_factory.create_unpaid_charge_reminder(
            self.reminder_repo, self.business_repo, self.charge_repo,
            client_record_id=client_record_id, **kwargs
        )

    def create_advance_payment_due_reminder(self, **kwargs):
        return reminder_factory.create_advance_payment_due_reminder(
            self.reminder_repo, self.business_repo, self.advance_payment_repo, **kwargs
        )

    def create_document_missing_reminder(self, **kwargs):
        return reminder_factory.create_document_missing_reminder(
            self.reminder_repo, self.business_repo, **kwargs
        )

    def create_custom_reminder(self, **kwargs):
        return reminder_factory.create_custom_reminder(
            self.reminder_repo, self.business_repo, **kwargs
        )

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_reminders(self, **kwargs):
        return reminder_queries.get_reminders(self.reminder_repo, self.client_repo, self.business_repo, self.tax_deadline_repo, **kwargs)

    def get_pending_reminders(self, **kwargs):
        return reminder_queries.get_pending_reminders(self.reminder_repo, self.client_repo, self.business_repo, self.tax_deadline_repo, **kwargs)

    def get_reminders_by_business(self, **kwargs):
        return reminder_queries.get_reminders_by_business(self.reminder_repo, self.client_repo, self.business_repo, self.tax_deadline_repo, **kwargs)

    def get_reminders_by_client(self, **kwargs):
        return reminder_queries.get_reminders_by_client(self.reminder_repo, self.client_repo, self.business_repo, self.tax_deadline_repo, **kwargs)

    def get_reminder(self, reminder_id: int):
        return reminder_queries.get_reminder(self.reminder_repo, reminder_id)

    # ── Status changes ────────────────────────────────────────────────────────

    def claim_for_processing(self, reminder_id: int):
        return self.reminder_repo.claim_for_processing(reminder_id)

    def mark_sent(self, reminder_id: int, actor_id: int):
        return status_changes.mark_sent(self.reminder_repo, reminder_id, actor_id=actor_id)

    def cancel_reminder(self, reminder_id: int, actor_id: int):
        return status_changes.cancel_reminder(self.reminder_repo, reminder_id, actor_id=actor_id)

    def cancel_reminders_for_charge(self, charge_id: int) -> int:
        return self.reminder_repo.cancel_pending_by_charge(charge_id)

    def cancel_reminders_for_tax_deadline(self, tax_deadline_id: int) -> int:
        return self.reminder_repo.cancel_pending_by_tax_deadline(tax_deadline_id)
