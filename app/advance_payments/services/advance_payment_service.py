from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.utils.time_utils import utcnow

from app.core.exceptions import ConflictError, NotFoundError
from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.repositories.advance_payment_analytics_repository import AdvancePaymentAnalyticsRepository
from app.advance_payments.services.advance_payment_calculator import (
    calculate_expected_amount,
    derive_annual_income_from_vat,
)
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.repositories.business_tax_profile_repository import BusinessTaxProfileRepository
from app.businesses.services.business_guards import assert_business_allows_create
from app.vat_reports.repositories.vat_client_summary_repository import VatClientSummaryRepository


class AdvancePaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdvancePaymentRepository(db)
        self.analytics_repo = AdvancePaymentAnalyticsRepository(db)

    @property
    def _business_repo(self) -> BusinessRepository:
        return BusinessRepository(self.db)

    @property
    def _tax_profile_repo(self) -> BusinessTaxProfileRepository:
        return BusinessTaxProfileRepository(self.db)

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
        business = self._business_repo.get_by_id(business_id)
        if not business:
            raise NotFoundError(f"עסק {business_id} לא נמצא", "ADVANCE_PAYMENT.BUSINESS_NOT_FOUND")
        assert_business_allows_create(business)

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

    # ─── Overview ─────────────────────────────────────────────────────────────

    def list_overview(
        self,
        year: int,
        month: Optional[int] = None,
        statuses: Optional[list[AdvancePaymentStatus]] = None,
        page: int = 1,
        page_size: int = 50,
    ):
        if statuses is None:
            statuses = list(AdvancePaymentStatus)

        payments = self.repo.list_overview_payments(year, month, statuses)

        business_ids = list({p.business_id for p in payments})
        businesses = {b.id: b for b in self._business_repo.list_by_ids(business_ids)}

        rows = sorted(
            [
                (
                    p,
                    (businesses[p.business_id].business_name or businesses[p.business_id].client.full_name)
                    if p.business_id in businesses else "",
                )
                for p in payments
            ],
            key=lambda x: (x[1], x[0].period),
        )

        total = len(rows)
        offset = (page - 1) * page_size
        return rows[offset: offset + page_size], total

    # ─── KPIs ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _collection_rate(total_paid: float, total_expected: float) -> float:
        return round(total_paid / total_expected * 100, 2) if total_expected > 0 else 0.0

    def get_annual_kpis(self, business_id: int, year: int) -> dict:
        if not self._business_repo.get_by_id(business_id):
            raise NotFoundError(f"עסק {business_id} לא נמצא", "ADVANCE_PAYMENT.BUSINESS_NOT_FOUND")
        data = self.analytics_repo.get_annual_kpis(business_id, year)
        return {
            **data,
            "business_id": business_id,
            "year": year,
            "collection_rate": self._collection_rate(data["total_paid"], data["total_expected"]),
        }

    def get_overview_kpis(
        self,
        year: int,
        month: Optional[int] = None,
        statuses: Optional[list[AdvancePaymentStatus]] = None,
    ) -> dict:
        if statuses is None:
            statuses = list(AdvancePaymentStatus)
        data = self.analytics_repo.get_overview_kpis(year, month, statuses)
        return {**data, "collection_rate": self._collection_rate(data["total_paid"], data["total_expected"])}

    def get_chart_data(self, business_id: int, year: int) -> dict:
        if not self._business_repo.get_by_id(business_id):
            raise NotFoundError(f"עסק {business_id} לא נמצא", "ADVANCE_PAYMENT.BUSINESS_NOT_FOUND")
        months = self.analytics_repo.monthly_chart_data(business_id, year)
        return {"business_id": business_id, "year": year, "months": months}

    # ─── Suggest ──────────────────────────────────────────────────────────────

    def suggest_expected_amount(
        self, business_id: int, year: int, period_months_count: int = 1
    ) -> Optional[Decimal]:
        """
        מחשב הצעה למקדמה לפי מע"מ עסקאות של השנה הקודמת + שיעור המקדמה.
        מחזיר None אם חסר מידע.
        """
        profile = self._tax_profile_repo.get_by_business_id(business_id)
        if profile is None or profile.advance_rate is None:
            return None

        prior_year_vat = VatClientSummaryRepository(self.db).get_annual_output_vat(
            business_id, year - 1
        )
        if prior_year_vat is None:
            return None

        annual_income = derive_annual_income_from_vat(prior_year_vat)
        return calculate_expected_amount(
            annual_income, Decimal(str(profile.advance_rate)), period_months_count
        )