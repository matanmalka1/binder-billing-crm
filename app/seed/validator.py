from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePayment
from app.annual_reports.models.annual_report_model import AnnualReport
from app.binders.models.binder import Binder
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.common.enums import EntityType, VatType
from app.tax_deadline.models.tax_deadline import TaxDeadline
from app.vat_reports.models.vat_work_item import VatWorkItem


class SeedIntegrityError(RuntimeError):
    pass


class SeedIntegrityValidator:
    def __init__(self, db: Session):
        self.db = db
        self._errors: list[str] = []

    def validate(self) -> None:
        self._errors = []
        self._check_active_clients_have_binders()
        self._check_no_vat_items_for_exempt_clients()
        self._check_no_duplicate_annual_reports()
        self._check_no_duplicate_tax_deadlines()
        if self._errors:
            error_list = "\n".join(f"  - {e}" for e in self._errors)
            raise SeedIntegrityError(
                f"Seed integrity check failed ({len(self._errors)} error(s)):\n{error_list}"
            )

    def _check_active_clients_have_binders(self) -> None:
        active_clients = (
            self.db.execute(select(ClientRecord.id).where(ClientRecord.deleted_at.is_(None)))
            .scalars()
            .all()
        )
        for client_id in active_clients:
            count = (
                self.db.execute(
                    select(func.count())
                    .select_from(Binder)
                    .where(Binder.client_record_id == client_id, Binder.deleted_at.is_(None))
                )
                .scalar_one()
            )
            if count == 0:
                self._errors.append(f"Client {client_id} has no binders")

    def _check_no_vat_items_for_exempt_clients(self) -> None:
        exempt_types = {EntityType.OSEK_PATUR, EntityType.EMPLOYEE}
        exempt_client_ids = (
            self.db.execute(
                select(ClientRecord.id)
                .join(LegalEntity, LegalEntity.id == ClientRecord.legal_entity_id)
                .where(LegalEntity.entity_type.in_(exempt_types), ClientRecord.deleted_at.is_(None))
            )
            .scalars()
            .all()
        )
        for client_id in exempt_client_ids:
            count = (
                self.db.execute(
                    select(func.count())
                    .select_from(VatWorkItem)
                    .where(VatWorkItem.client_record_id == client_id, VatWorkItem.deleted_at.is_(None))
                )
                .scalar_one()
            )
            if count > 0:
                self._errors.append(
                    f"Client {client_id} is EXEMPT but has {count} VAT work item(s)"
                )

    def _check_no_duplicate_annual_reports(self) -> None:
        dupes = (
            self.db.execute(
                select(AnnualReport.client_record_id, AnnualReport.tax_year, func.count())
                .where(AnnualReport.deleted_at.is_(None))
                .group_by(AnnualReport.client_record_id, AnnualReport.tax_year)
                .having(func.count() > 1)
            )
            .all()
        )
        for client_id, tax_year, count in dupes:
            self._errors.append(
                f"Client {client_id} has {count} annual reports for year {tax_year}"
            )

    def _check_no_duplicate_tax_deadlines(self) -> None:
        dupes = (
            self.db.execute(
                select(
                    TaxDeadline.client_record_id,
                    TaxDeadline.deadline_type,
                    TaxDeadline.period,
                    func.count(),
                )
                .where(TaxDeadline.deleted_at.is_(None), TaxDeadline.period.isnot(None))
                .group_by(TaxDeadline.client_record_id, TaxDeadline.deadline_type, TaxDeadline.period)
                .having(func.count() > 1)
            )
            .all()
        )
        for client_id, deadline_type, period, count in dupes:
            self._errors.append(
                f"Client {client_id} has {count} {deadline_type} deadlines for period {period}"
            )
