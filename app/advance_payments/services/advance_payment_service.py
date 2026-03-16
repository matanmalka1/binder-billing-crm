from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.repositories.advance_payment_analytics_repository import AdvancePaymentAnalyticsRepository
from app.advance_payments.services.advance_payment_calculator import (
    calculate_expected_amount,
    derive_annual_income_from_vat,
)
from app.clients.repositories.client_repository import ClientRepository
from app.clients.repositories.client_tax_profile_repository import ClientTaxProfileRepository
from app.vat_reports.repositories.vat_client_summary_repository import VatClientSummaryRepository


class AdvancePaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdvancePaymentRepository(db)
        self.analytics_repo = AdvancePaymentAnalyticsRepository(db)

    @property
    def _client_repo(self) -> ClientRepository:
        return ClientRepository(self.db)

    @property
    def _tax_profile_repo(self) -> ClientTaxProfileRepository:
        return ClientTaxProfileRepository(self.db)

    def list_payments(
        self,
        client_id: int,
        year: int,
        status: Optional[list[AdvancePaymentStatus]] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AdvancePayment], int]:
        if not self._client_repo.get_by_id(client_id):
            raise NotFoundError("Client not found", "ADVANCE_PAYMENT.CLIENT_NOT_FOUND")
        return self.repo.list_by_client_year(client_id, year, status=status, page=page, page_size=page_size)

    def create_payment(
        self,
        client_id: int,
        year: int,
        month: int,
        due_date,
        expected_amount=None,
        paid_amount=None,
        tax_deadline_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> AdvancePayment:
        # Validate client exists
        if not self._client_repo.get_by_id(client_id):
            raise NotFoundError("Client not found", "ADVANCE_PAYMENT.NOT_FOUND")

        if self.repo.exists_for_month(client_id, year, month):
            raise ConflictError("תשלום מקדמה לחודש זה כבר קיים", "ADVANCE_PAYMENT.CONFLICT")

        return self.repo.create(
            client_id=client_id,
            year=year,
            month=month,
            due_date=due_date,
            expected_amount=expected_amount,
            paid_amount=paid_amount,
            tax_deadline_id=tax_deadline_id,
            notes=notes,
        )

    def delete_payment(self, payment_id: int) -> None:
        payment = self.repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError(f"Advance payment {payment_id} not found", "ADVANCE_PAYMENT.NOT_FOUND")
        self.repo.delete(payment)

    _ALLOWED_UPDATE_FIELDS = {"paid_amount", "expected_amount", "status", "notes"}

    def update_payment(self, payment_id: int, **fields) -> AdvancePayment:
        payment = self.repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError(f"Advance payment {payment_id} not found", "ADVANCE_PAYMENT.NOT_FOUND")

        filtered = {k: v for k, v in fields.items() if k in self._ALLOWED_UPDATE_FIELDS}
        return self.repo.update(payment, **filtered)

    def list_overview(
        self,
        year: int,
        month=None,
        statuses=None,
        page: int = 1,
        page_size: int = 50,
    ):
        if statuses is None:
            statuses = [
                AdvancePaymentStatus.PENDING,
                AdvancePaymentStatus.OVERDUE,
                AdvancePaymentStatus.PARTIAL,
                AdvancePaymentStatus.PAID,
            ]
        payments = self.repo.list_overview_payments(year, month, statuses)
        client_ids = list({p.client_id for p in payments})
        clients = {c.id: c.full_name for c in self._client_repo.list_by_ids(client_ids)}
        rows = sorted(
            [(p, clients.get(p.client_id, "")) for p in payments],
            key=lambda x: (x[1], x[0].month),
        )
        total = len(rows)
        offset = (page - 1) * page_size
        return rows[offset : offset + page_size], total

    def get_annual_kpis(self, client_id: int, year: int) -> dict:
        if not self._client_repo.get_by_id(client_id):
            raise NotFoundError("Client not found", "CLIENT.NOT_FOUND")
        data = self.analytics_repo.get_annual_kpis(client_id, year)
        total_expected = data["total_expected"]
        total_paid = data["total_paid"]
        collection_rate = (total_paid / total_expected * 100) if total_expected > 0 else 0.0
        return {**data, "client_id": client_id, "year": year, "collection_rate": round(collection_rate, 2)}

    def get_overview_kpis(self, year: int, month=None, statuses=None) -> dict:
        if statuses is None:
            statuses = [
                AdvancePaymentStatus.PENDING,
                AdvancePaymentStatus.OVERDUE,
                AdvancePaymentStatus.PARTIAL,
                AdvancePaymentStatus.PAID,
            ]
        data = self.analytics_repo.get_overview_kpis(year, month, statuses)
        total_expected = data["total_expected"]
        total_paid = data["total_paid"]
        collection_rate = (total_paid / total_expected * 100) if total_expected > 0 else 0.0
        return {**data, "collection_rate": round(collection_rate, 2)}

    def get_chart_data(self, client_id: int, year: int) -> dict:
        if not self._client_repo.get_by_id(client_id):
            raise NotFoundError("Client not found", "CLIENT.NOT_FOUND")
        months = self.analytics_repo.monthly_chart_data(client_id, year)
        return {"client_id": client_id, "year": year, "months": months}

    def suggest_expected_amount(
        self, client_id: int, year: int
    ) -> Optional[Decimal]:
        """
        Return a monthly advance suggestion based on prior year VAT output and
        the client's advance_rate. Returns None if either is missing.
        """
        profile = self._tax_profile_repo.get_by_client_id(client_id)
        if profile is None or profile.advance_rate is None:
            return None

        prior_year_vat = VatClientSummaryRepository(self.db).get_annual_output_vat(client_id, year - 1)
        if prior_year_vat is None:
            return None

        annual_income = derive_annual_income_from_vat(prior_year_vat)
        return calculate_expected_amount(annual_income, Decimal(str(profile.advance_rate)))
