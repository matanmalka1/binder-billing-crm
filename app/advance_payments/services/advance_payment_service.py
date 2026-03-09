from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.advance_payment_calculator import (
    calculate_expected_amount,
    derive_annual_income_from_vat,
)
from app.clients.repositories.client_repository import ClientRepository
from app.clients.repositories.client_tax_profile_repository import ClientTaxProfileRepository


class AdvancePaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdvancePaymentRepository(db)
        self.client_repo = ClientRepository(db)
        self.tax_profile_repo = ClientTaxProfileRepository(db)

    def list_payments(
        self,
        client_id: int,
        year: int,
        status: Optional[AdvancePaymentStatus] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AdvancePayment], int]:
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
        if not self.client_repo.get_by_id(client_id):
            raise NotFoundError("Client not found", "ADVANCE_PAYMENT.NOT_FOUND")

        existing, _ = self.repo.list_by_client_year(client_id, year, page=1, page_size=12)
        if any(p.month == month for p in existing):
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
            ]
        return self.repo.list_overview(year, month, statuses, page=page, page_size=page_size)

    def get_annual_kpis(self, client_id: int, year: int) -> dict:
        if not self.client_repo.get_by_id(client_id):
            raise NotFoundError("Client not found", "CLIENT.NOT_FOUND")
        data = self.repo.get_annual_kpis(client_id, year)
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
            ]
        data = self.repo.get_overview_kpis(year, month, statuses)
        total_expected = data["total_expected"]
        total_paid = data["total_paid"]
        collection_rate = (total_paid / total_expected * 100) if total_expected > 0 else 0.0
        return {**data, "collection_rate": round(collection_rate, 2)}

    def suggest_expected_amount(
        self, client_id: int, year: int
    ) -> Optional[Decimal]:
        """
        Return a monthly advance suggestion based on prior year VAT output and
        the client's advance_rate. Returns None if either is missing.
        """
        profile = self.tax_profile_repo.get_by_client_id(client_id)
        if profile is None or profile.advance_rate is None:
            return None

        prior_year_vat = self.repo.get_annual_output_vat(client_id, year - 1)
        if prior_year_vat is None:
            return None

        annual_income = derive_annual_income_from_vat(prior_year_vat)
        return calculate_expected_amount(annual_income, Decimal(str(profile.advance_rate)))
