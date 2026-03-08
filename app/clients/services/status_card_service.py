from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.clients.repositories.client_repository import ClientRepository
from app.clients.schemas.client_status_card import (
    AdvancePaymentsCard,
    AnnualReportCard,
    BindersCard,
    ChargesCard,
    ClientStatusCardResponse,
    DocumentsCard,
    VatSummaryCard,
)
from app.vat_reports.models.vat_work_item import VatWorkItem, VatWorkItemStatus
from app.annual_reports.models.annual_report_model import AnnualReport
from app.charge.models.charge import Charge, ChargeStatus
from app.advance_payments.models.advance_payment import AdvancePayment
from app.binders.models.binder import Binder, BinderStatus
from app.permanent_documents.models.permanent_document import PermanentDocument


class StatusCardService:
    def __init__(self, db: Session):
        self._db = db
        self._client_repo = ClientRepository(db)

    def get_status_card(self, client_id: int) -> ClientStatusCardResponse:
        client = self._client_repo.get_by_id(client_id)
        if not client:
            raise ValueError("הלקוח לא נמצא")

        year = datetime.utcnow().year
        return ClientStatusCardResponse(
            client_id=client_id,
            year=year,
            vat=self._vat_card(client_id, year),
            annual_report=self._annual_report_card(client_id, year),
            charges=self._charges_card(client_id),
            advance_payments=self._advance_payments_card(client_id, year),
            binders=self._binders_card(client_id),
            documents=self._documents_card(client_id),
        )

    def _vat_card(self, client_id: int, year: int) -> VatSummaryCard:
        prefix = f"{year}-"
        rows = (
            self._db.query(VatWorkItem)
            .filter(
                VatWorkItem.client_id == client_id,
                VatWorkItem.period.startswith(prefix),
            )
            .all()
        )
        net_total = sum((r.net_vat or Decimal(0)) for r in rows)
        filed = sum(1 for r in rows if r.status == VatWorkItemStatus.FILED)
        latest = max((r.period for r in rows), default=None)
        return VatSummaryCard(
            net_vat_total=net_total,
            periods_filed=filed,
            periods_total=len(rows),
            latest_period=latest,
        )

    def _annual_report_card(self, client_id: int, year: int) -> AnnualReportCard:
        report: Optional[AnnualReport] = (
            self._db.query(AnnualReport)
            .filter(AnnualReport.client_id == client_id, AnnualReport.tax_year == year)
            .first()
        )
        if not report:
            return AnnualReportCard()
        deadline_str = (
            report.filing_deadline.strftime("%Y-%m-%d") if report.filing_deadline else None
        )
        return AnnualReportCard(
            status=report.status.value if report.status else None,
            form_type=report.form_type.value if report.form_type else None,
            filing_deadline=deadline_str,
            refund_due=report.refund_due,
            tax_due=report.tax_due,
        )

    def _charges_card(self, client_id: int) -> ChargesCard:
        rows = (
            self._db.query(Charge)
            .filter(Charge.client_id == client_id, Charge.status == ChargeStatus.ISSUED)
            .all()
        )
        total = sum((r.amount or Decimal(0)) for r in rows)
        return ChargesCard(total_outstanding=total, unpaid_count=len(rows))

    def _advance_payments_card(self, client_id: int, year: int) -> AdvancePaymentsCard:
        rows = (
            self._db.query(AdvancePayment)
            .filter(AdvancePayment.client_id == client_id, AdvancePayment.year == year)
            .all()
        )
        total = sum((r.paid_amount or Decimal(0)) for r in rows)
        return AdvancePaymentsCard(total_paid=total, count=len(rows))

    def _binders_card(self, client_id: int) -> BindersCard:
        rows = (
            self._db.query(Binder)
            .filter(
                Binder.client_id == client_id,
                Binder.status != BinderStatus.RETURNED,
            )
            .all()
        )
        in_office = sum(1 for r in rows if r.status == BinderStatus.IN_OFFICE)
        return BindersCard(active_count=len(rows), in_office_count=in_office)

    def _documents_card(self, client_id: int) -> DocumentsCard:
        rows = (
            self._db.query(PermanentDocument)
            .filter(PermanentDocument.client_id == client_id)
            .all()
        )
        present = sum(1 for r in rows if r.is_present)
        return DocumentsCard(total_count=len(rows), present_count=present)
