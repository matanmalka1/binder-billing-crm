from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.utils.time_utils import utcnow
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.advance_payment_calculator import (
    calculate_expected_amount,
    derive_annual_income_from_vat,
)
from app.advance_payments.services.constants import ADVANCE_PAYMENT_VAT_RATE
from app.clients.models.client import ClientStatus
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.vat_reports.repositories.vat_client_summary_repository import VatClientSummaryRepository


class AdvancePaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdvancePaymentRepository(db)

    def _get_record_or_raise(self, client_record_id: int):
        record = ClientRecordRepository(self.db).get_by_id(client_record_id)
        if record is None:
            raise NotFoundError(f"רשומת לקוח {client_record_id} לא נמצאה", "ADVANCE_PAYMENT.CLIENT_RECORD_NOT_FOUND")
        return record

    def _assert_client_allows_create(self, client_record_id: int) -> None:
        record = self._get_record_or_raise(client_record_id)
        if record.status == ClientStatus.CLOSED:
            raise ForbiddenError("לקוח סגור — לא ניתן ליצור מקדמה", "CLIENT.CLOSED")
        if record.status == ClientStatus.FROZEN:
            raise ForbiddenError("לקוח מוקפא — לא ניתן ליצור מקדמה", "CLIENT.FROZEN")

    # ─── List ─────────────────────────────────────────────────────────────────

    def list_payments_for_client(
        self,
        client_record_id: int,
        year: Optional[int] = None,
        status: Optional[list[AdvancePaymentStatus]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AdvancePayment], int]:
        if year is None:
            year = utcnow().year
        self._get_record_or_raise(client_record_id)
        return self.repo.list_by_client_record_year(
            client_record_id, year, status=status, page=page, page_size=page_size
        )

    # ─── Create ───────────────────────────────────────────────────────────────

    def create_payment_for_client(
        self,
        client_record_id: int,
        period: str,
        period_months_count: int,
        due_date,
        expected_amount=None,
        paid_amount=None,
        payment_method=None,
        annual_report_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> AdvancePayment:
        self._assert_client_allows_create(client_record_id)
        if self.repo.exists_for_period(client_record_id, period):
            raise ConflictError(
                f"תשלום מקדמה לתקופה {period} כבר קיים",
                "ADVANCE_PAYMENT.CONFLICT",
            )
        return self.repo.create(
            client_record_id=client_record_id,
            period=period,
            period_months_count=period_months_count,
            due_date=due_date,
            expected_amount=expected_amount,
            paid_amount=paid_amount,
            payment_method=payment_method,
            annual_report_id=annual_report_id,
            notes=notes,
        )

    # ─── Update ───────────────────────────────────────────────────────────────

    _ALLOWED_UPDATE_FIELDS = {
        "paid_amount", "expected_amount", "status",
        "paid_at", "payment_method", "notes",
    }

    def update_payment_for_client(self, client_record_id: int, payment_id: int, **fields) -> AdvancePayment:
        self._get_record_or_raise(client_record_id)
        payment = self.repo.get_by_id_for_client_record(payment_id, client_record_id)
        if not payment:
            raise NotFoundError(
                f"תשלום מקדמה {payment_id} לא נמצא עבור לקוח {client_record_id}",
                "ADVANCE_PAYMENT.NOT_FOUND",
            )
        filtered = {k: v for k, v in fields.items() if k in self._ALLOWED_UPDATE_FIELDS}

        if "paid_amount" in filtered and "status" not in filtered:
            paid = filtered["paid_amount"]
            expected = filtered.get("expected_amount", payment.expected_amount)
            if paid is None or paid == 0:
                filtered["status"] = AdvancePaymentStatus.PENDING
            elif expected is not None and paid >= expected:
                filtered["status"] = AdvancePaymentStatus.PAID
            else:
                filtered["status"] = AdvancePaymentStatus.PARTIAL

        return self.repo.update(payment, **filtered)

    # ─── Delete ───────────────────────────────────────────────────────────────

    def delete_payment_for_client(self, client_record_id: int, payment_id: int, actor_id: int) -> None:
        self._get_record_or_raise(client_record_id)
        payment = self.repo.get_by_id_for_client_record(payment_id, client_record_id)
        if not payment:
            raise NotFoundError(
                f"תשלום מקדמה {payment_id} לא נמצא עבור לקוח {client_record_id}",
                "ADVANCE_PAYMENT.NOT_FOUND",
            )
        self.repo.soft_delete(payment_id, deleted_by=actor_id)

    # ─── Suggest ─────────────────────────────────────────────────────────────

    def suggest_expected_amount_for_client(
        self, client_record_id: int, year: int, period_months_count: int = 1
    ) -> Optional[Decimal]:
        record = self._get_record_or_raise(client_record_id)
        legal_entity = LegalEntityRepository(self.db).get_by_id(record.legal_entity_id)
        if legal_entity is None or legal_entity.advance_rate is None:
            return None
        prior_year_vat = VatClientSummaryRepository(self.db).get_annual_output_vat(
            client_record_id=client_record_id, year=year - 1
        )
        if prior_year_vat is None:
            return None
        annual_income = derive_annual_income_from_vat(prior_year_vat, ADVANCE_PAYMENT_VAT_RATE)
        return calculate_expected_amount(
            annual_income, Decimal(str(legal_entity.advance_rate)), period_months_count
        )
