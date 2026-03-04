from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

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
        self, client_id: int, year: int, page: int = 1, page_size: int = 50
    ) -> tuple[list[AdvancePayment], int]:
        return self.repo.list_by_client_year(client_id, year, page=page, page_size=page_size)

    def create_payment(
        self,
        client_id: int,
        year: int,
        month: int,
        due_date,
        expected_amount=None,
        paid_amount=None,
        tax_deadline_id: Optional[int] = None,
    ) -> AdvancePayment:
        # Validate client exists
        if not self.client_repo.get_by_id(client_id):
            raise LookupError("Client not found")

        if month < 1 or month > 12:
            raise ValueError("month must be between 1 and 12")

        existing, _ = self.repo.list_by_client_year(client_id, year, page=1, page_size=12)
        if any(p.month == month for p in existing):
            raise RuntimeError("Advance payment for this month already exists")

        return self.repo.create(
            client_id=client_id,
            year=year,
            month=month,
            due_date=due_date,
            expected_amount=expected_amount,
            paid_amount=paid_amount,
            tax_deadline_id=tax_deadline_id,
        )

    def update_payment(self, payment_id: int, **fields) -> AdvancePayment:
        payment = self.repo.get_by_id(payment_id)
        if not payment:
            raise ValueError(f"Advance payment {payment_id} not found")

        if "status" in fields and fields["status"] is not None:
            try:
                AdvancePaymentStatus(fields["status"])
            except ValueError:
                raise ValueError(
                    f"Invalid status: {fields['status']}. "
                    f"Must be one of: pending, paid, partial, overdue"
                )

        updated = self.repo.update(payment_id, **fields)
        return updated

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
