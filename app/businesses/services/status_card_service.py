from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.businesses.models.business import Business as _Business
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.schemas.business_status_card import (
    AdvancePaymentsCard,
    AnnualReportCard,
    BindersCard,
    BusinessStatusCardResponse,
    ChargesCard,
    DocumentsCard,
    VatSummaryCard,
)
from app.utils.time_utils import utcnow
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.models.vat_work_item import VatWorkItemStatus
from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.charge.models.charge import ChargeStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.models.binder import BinderStatus
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository


class StatusCardService:
    """
    Status card ללקוח ספציפי.
    endpoint: GET /clients/{client_id}/status-card
    """

    def __init__(self, db: Session):
        self._db = db
        self._business_repo = BusinessRepository(db)
        self._vat_repo = VatWorkItemRepository(db)
        self._annual_repo = AnnualReportRepository(db)
        self._charge_repo = ChargeRepository(db)
        self._advance_repo = AdvancePaymentRepository(db)
        self._binder_repo = BinderRepository(db)
        self._doc_repo = PermanentDocumentRepository(db)

    def get_status_card(
        self,
        client_id: int,
        year: Optional[int] = None,
    ) -> BusinessStatusCardResponse:
        # Use the first non-deleted business for business-scoped data (annual reports, charges, advances, documents).
        business = (
            self._db.query(_Business)
            .filter(_Business.client_id == client_id, _Business.deleted_at.is_(None))
            .first()
        )
        if not business:
            raise NotFoundError("לא נמצא עסק עבור לקוח זה", "BUSINESS.NOT_FOUND")

        business_id = business.id
        resolved_year = year or utcnow().year
        return BusinessStatusCardResponse(
            client_id=client_id,
            business_id=business_id,
            year=resolved_year,
            client_vat=self._vat_card(client_id, resolved_year),
            annual_report=self._annual_report_card(business_id, resolved_year),
            charges=self._charges_card(business_id),
            advance_payments=self._advance_payments_card(business_id, resolved_year),
            binders=self._binders_card(client_id),
            documents=self._documents_card(business_id),
        )

    def _vat_card(self, client_id: int, year: int) -> VatSummaryCard:
        prefix = f"{year}-"
        rows = [
            r for r in self._vat_repo.list_by_client(client_id)
            if r.period and r.period.startswith(prefix)
        ]
        net_total = sum((r.net_vat or Decimal(0)) for r in rows)
        filed = sum(1 for r in rows if r.status == VatWorkItemStatus.FILED)
        latest = max((r.period for r in rows), default=None)
        return VatSummaryCard(
            net_vat_total=net_total,
            periods_filed=filed,
            periods_total=len(rows),
            latest_period=latest,
        )

    def _annual_report_card(self, business_id: int, year: int) -> AnnualReportCard:
        report = self._annual_repo.get_by_business_year(business_id, year)
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

    def _charges_card(self, business_id: int) -> ChargesCard:
        rows = self._charge_repo.list_charges(
            business_id=business_id,
            status=ChargeStatus.ISSUED,
            page=1,
            page_size=10_000,
        )
        total = sum((r.amount or Decimal(0)) for r in rows)
        return ChargesCard(total_outstanding=total, unpaid_count=len(rows))

    def _advance_payments_card(self, business_id: int, year: int) -> AdvancePaymentsCard:
        rows, _ = self._advance_repo.list_by_business_year(
            business_id=business_id,
            year=year,
            page=1,
            page_size=10_000,
        )
        total = sum((r.paid_amount or Decimal(0)) for r in rows)
        return AdvancePaymentsCard(total_paid=total, count=len(rows))

    def _binders_card(self, client_id: int) -> BindersCard:
        rows = self._binder_repo.list_by_client(client_id)
        active = [r for r in rows if r.status != BinderStatus.RETURNED]
        in_office = sum(1 for r in active if r.status == BinderStatus.IN_OFFICE)
        return BindersCard(active_count=len(active), in_office_count=in_office)

    def _documents_card(self, business_id: int) -> DocumentsCard:
        rows = self._doc_repo.list_by_business(business_id)
        present = sum(1 for r in rows if r.is_present)
        return DocumentsCard(total_count=len(rows), present_count=present)
