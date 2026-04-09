from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.utils.time_utils import utcnow
from app.core.exceptions import ConflictError, NotFoundError
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.advance_payment_calculator import (
    calculate_expected_amount,
    derive_annual_income_from_vat,
)
from app.advance_payments.services.constants import VAT_RATE
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_guards import validate_business_for_create
from app.clients.repositories.client_repository import ClientRepository
from app.vat_reports.repositories.vat_client_summary_repository import VatClientSummaryRepository


class AdvancePaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdvancePaymentRepository(db)

    @property
    def _business_repo(self) -> BusinessRepository:
        return BusinessRepository(self.db)

    @property
    def _client_repo(self) -> ClientRepository:
        return ClientRepository(self.db)

    def _ensure_client_exists(self, client_id: int):
        client = self._client_repo.get_by_id(client_id)
        if client is None:
            raise NotFoundError(f"לקוח {client_id} לא נמצא", "ADVANCE_PAYMENT.CLIENT_NOT_FOUND")
        return client

    def _ensure_business_belongs_to_client(self, client_id: int, business_id: int):
        business = self._business_repo.get_by_id(business_id)
        if business is None:
            raise NotFoundError(f"עסק {business_id} לא נמצא", "ADVANCE_PAYMENT.BUSINESS_NOT_FOUND")
        if business.client_id != client_id:
            raise NotFoundError(
                f"תשלום מקדמה עבור עסק {business_id} לא נמצא עבור לקוח {client_id}",
                "ADVANCE_PAYMENT.NOT_FOUND",
            )
        return business

    def validate_business_for_client(self, client_id: int, business_id: int):
        self._ensure_client_exists(client_id)
        return self._ensure_business_belongs_to_client(client_id, business_id)

    # ─── List ─────────────────────────────────────────────────────────────────

    def list_payments(
        self,
        business_id: int,
        year: Optional[int] = None,
        status: Optional[list[AdvancePaymentStatus]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AdvancePayment], int]:
        if year is None:
            year = utcnow().year
        if not self._business_repo.get_by_id(business_id):
            raise NotFoundError(f"עסק {business_id} לא נמצא", "ADVANCE_PAYMENT.BUSINESS_NOT_FOUND")
        return self.repo.list_by_business_year(
            business_id, year, status=status, page=page, page_size=page_size
        )

    def list_payments_for_client(
        self,
        client_id: int,
        year: Optional[int] = None,
        status: Optional[list[AdvancePaymentStatus]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AdvancePayment], int]:
        if year is None:
            year = utcnow().year
        self._ensure_client_exists(client_id)
        return self.repo.list_by_client_year(
            client_id, year, status=status, page=page, page_size=page_size
        )

    # ─── Create ───────────────────────────────────────────────────────────────

    def create_payment(
        self,
        business_id: int,
        period: str,
        period_months_count: int,
        due_date,
        expected_amount=None,
        paid_amount=None,
        payment_method=None,
        annual_report_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> AdvancePayment:
        try:
            validate_business_for_create(self.db, business_id)
        except NotFoundError as exc:
            raise NotFoundError(
                f"עסק {business_id} לא נמצא",
                "ADVANCE_PAYMENT.BUSINESS_NOT_FOUND",
            ) from exc

        if self.repo.exists_for_period(business_id, period):
            raise ConflictError(
                f"תשלום מקדמה לתקופה {period} כבר קיים",
                "ADVANCE_PAYMENT.CONFLICT",
            )

        return self.repo.create(
            business_id=business_id,
            period=period,
            period_months_count=period_months_count,
            due_date=due_date,
            expected_amount=expected_amount,
            paid_amount=paid_amount,
            payment_method=payment_method,
            annual_report_id=annual_report_id,
            notes=notes,
        )

    def create_payment_for_client(
        self,
        client_id: int,
        business_id: int,
        period: str,
        period_months_count: int,
        due_date,
        expected_amount=None,
        paid_amount=None,
        payment_method=None,
        annual_report_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> AdvancePayment:
        self._ensure_client_exists(client_id)
        self._ensure_business_belongs_to_client(client_id, business_id)
        return self.create_payment(
            business_id=business_id,
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

    def update_payment(self, business_id: int, payment_id: int, **fields) -> AdvancePayment:
        payment = self.repo.get_by_id_for_business(payment_id, business_id)
        if not payment:
            raise NotFoundError(
                f"תשלום מקדמה {payment_id} לא נמצא עבור עסק {business_id}",
                "ADVANCE_PAYMENT.NOT_FOUND",
            )
        filtered = {k: v for k, v in fields.items() if k in self._ALLOWED_UPDATE_FIELDS}

        # Auto-derive status from paid_amount unless the caller is explicitly setting status.
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

    def update_payment_for_client(self, client_id: int, payment_id: int, **fields) -> AdvancePayment:
        self._ensure_client_exists(client_id)
        payment = self.repo.get_by_id_for_client(payment_id, client_id)
        if not payment:
            raise NotFoundError(
                f"תשלום מקדמה {payment_id} לא נמצא עבור לקוח {client_id}",
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

    def delete_payment(self, business_id: int, payment_id: int, actor_id: int) -> None:
        payment = self.repo.get_by_id_for_business(payment_id, business_id)
        if not payment:
            raise NotFoundError(
                f"תשלום מקדמה {payment_id} לא נמצא עבור עסק {business_id}",
                "ADVANCE_PAYMENT.NOT_FOUND",
            )
        self.repo.soft_delete(payment_id, deleted_by=actor_id)

    def delete_payment_for_client(self, client_id: int, payment_id: int, actor_id: int) -> None:
        self._ensure_client_exists(client_id)
        payment = self.repo.get_by_id_for_client(payment_id, client_id)
        if not payment:
            raise NotFoundError(
                f"תשלום מקדמה {payment_id} לא נמצא עבור לקוח {client_id}",
                "ADVANCE_PAYMENT.NOT_FOUND",
            )
        self.repo.soft_delete(payment_id, deleted_by=actor_id)

    # ─── Suggest ─────────────────────────────────────────────────────────────
    def suggest_expected_amount(
        self, business_id: int, year: int, period_months_count: int = 1
    ) -> Optional[Decimal]:
        """מחשב הצעה למקדמה לפי מע"מ עסקאות של השנה הקודמת + שיעור המקדמה. מחזיר None אם חסר מידע."""
        business = self._business_repo.get_by_id(business_id)
        if business is None:
            return None
        client = self._client_repo.get_by_id(business.client_id)
        if client is None:
            return None
        advance_rate = client.advance_rate
        if advance_rate is None:
            return None

        prior_year_vat = VatClientSummaryRepository(self.db).get_annual_output_vat(
            client_id=business.client_id, year=year - 1
        )
        if prior_year_vat is None:
            return None

        annual_income = derive_annual_income_from_vat(prior_year_vat, VAT_RATE)
        return calculate_expected_amount(
            annual_income, Decimal(str(advance_rate)), period_months_count
        )

    def suggest_expected_amount_for_client(
        self, client_id: int, year: int, period_months_count: int = 1
    ) -> Optional[Decimal]:
        client = self._client_repo.get_by_id(client_id)
        if client is None:
            return None
        advance_rate = client.advance_rate
        if advance_rate is None:
            return None

        prior_year_vat = VatClientSummaryRepository(self.db).get_annual_output_vat(
            client_id=client_id, year=year - 1
        )
        if prior_year_vat is None:
            return None

        annual_income = derive_annual_income_from_vat(prior_year_vat, VAT_RATE)
        return calculate_expected_amount(
            annual_income, Decimal(str(advance_rate)), period_months_count
        )
