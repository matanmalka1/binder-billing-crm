from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from random import Random

from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus, PaymentMethod
from app.businesses.models.business import BusinessType
from app.tax_deadline.models.tax_deadline import (
    TaxDeadline,
    DeadlineType as TaxDeadlineType,
    TaxDeadlineStatus,
)

from ._business_groups import group_businesses_by_client, pick_businesses_for_client


# Hebrew labels for deadline types used in seed descriptions
DEADLINE_LABELS = {
    TaxDeadlineType.ADVANCE_PAYMENT: "מקדמה",
    TaxDeadlineType.ANNUAL_REPORT: "דוח שנתי",
    TaxDeadlineType.NATIONAL_INSURANCE: "ביטוח לאומי",
    TaxDeadlineType.VAT: 'מע"מ',
    TaxDeadlineType.OTHER: "אחר",
}


def _eligible_deadline_types(business) -> list[TaxDeadlineType]:
    client = business.client
    types = [
        TaxDeadlineType.ANNUAL_REPORT,
        TaxDeadlineType.NATIONAL_INSURANCE,
        TaxDeadlineType.OTHER,
    ]
    if client.vat_reporting_frequency in ("monthly", "bimonthly"):
        types.append(TaxDeadlineType.VAT)
    if business.business_type != BusinessType.EMPLOYEE and client.advance_rate is not None:
        types.append(TaxDeadlineType.ADVANCE_PAYMENT)
    return types


def create_tax_deadlines(db, rng: Random, cfg, businesses, users=None) -> list[TaxDeadline]:
    deadlines: list[TaxDeadline] = []
    today = date.today()
    for client_businesses in group_businesses_by_client(businesses).values():
        num = rng.randint(
            cfg.min_tax_deadlines_per_client,
            cfg.max_tax_deadlines_per_client,
        )
        for business in pick_businesses_for_client(rng, client_businesses, num):
            due_offset = rng.randint(-30, 60)
            due_date = today + timedelta(days=due_offset)
            deadline_type = rng.choice(_eligible_deadline_types(business))
            status = (
                TaxDeadlineStatus.COMPLETED
                if due_date < today and rng.random() < 0.5
                else TaxDeadlineStatus.PENDING
            )
            completed_at = None
            completed_by = None
            created_at = datetime.now(UTC) - timedelta(days=rng.randint(0, 120))
            if status == TaxDeadlineStatus.COMPLETED:
                due_datetime = datetime.combine(due_date, datetime.min.time(), tzinfo=UTC)
                earliest_completion = max(created_at, due_datetime - timedelta(days=14))
                latest_completion = min(datetime.now(UTC), due_datetime + timedelta(days=14))
                if latest_completion < earliest_completion:
                    latest_completion = earliest_completion
                window_seconds = int((latest_completion - earliest_completion).total_seconds())
                completed_at = earliest_completion + timedelta(
                    seconds=rng.randint(0, max(window_seconds, 1))
                )
                completed_by = rng.choice(users).id if users else None
            payment_amount = Decimal(str(round(rng.uniform(500, 15000), 2)))
            period = f"{due_date.year}-{due_date.month:02d}" if deadline_type != TaxDeadlineType.OTHER else None
            description = f"תזכורת עבור {DEADLINE_LABELS.get(deadline_type, 'מועד מס')}"
            deadline = TaxDeadline(
                client_id=business.client_id,
                deadline_type=deadline_type,
                period=period,
                due_date=due_date,
                status=status,
                payment_amount=payment_amount,
                description=description,
                created_at=created_at,
                completed_at=completed_at,
                completed_by=completed_by,
            )
            db.add(deadline)
            deadlines.append(deadline)
    db.flush()
    return deadlines


def create_advance_payments(db, rng: Random, businesses, deadlines) -> list[AdvancePayment]:
    payments: list[AdvancePayment] = []
    eligible_businesses = [
        business for business in businesses if business.business_type != BusinessType.EMPLOYEE
    ]
    deadlines_by_client_period = {}
    for dl in deadlines:
        if dl.period:
            deadlines_by_client_period[(dl.client_id, dl.period)] = dl

    for client_businesses in group_businesses_by_client(eligible_businesses).values():
        year = date.today().year
        months = sorted(rng.sample(range(1, 13), k=rng.randint(3, 7)))
        for month in months:
            business = rng.choice(client_businesses)
            period = f"{year}-{month:02d}"
            due_date = date(year, month, min(rng.randint(10, 28), 28))
            deadline = deadlines_by_client_period.get((business.client_id, period))
            status = rng.choice(list(AdvancePaymentStatus))
            expected_amount = Decimal(str(round(rng.uniform(500, 6000), 2)))
            paid_amount = Decimal("0.00")
            if status in (AdvancePaymentStatus.PAID, AdvancePaymentStatus.PARTIAL):
                paid_amount = Decimal(str(round(rng.uniform(200, float(expected_amount)), 2)))
            if status == AdvancePaymentStatus.OVERDUE:
                due_date = min(due_date, date.today() - timedelta(days=rng.randint(1, 60)))
            if status == AdvancePaymentStatus.PAID:
                paid_amount = expected_amount
            elif status == AdvancePaymentStatus.PARTIAL:
                paid_amount = min(expected_amount - Decimal("1.00"), paid_amount)
                if paid_amount <= Decimal("0.00"):
                    paid_amount = (expected_amount * Decimal("0.5")).quantize(Decimal("0.01"))
            elif status in (AdvancePaymentStatus.PENDING, AdvancePaymentStatus.OVERDUE):
                paid_amount = Decimal("0.00")

            created_at = datetime.now(UTC) - timedelta(days=rng.randint(0, 200))
            paid_at = None
            if status in (AdvancePaymentStatus.PAID, AdvancePaymentStatus.PARTIAL):
                paid_at = datetime.combine(due_date, datetime.min.time(), tzinfo=UTC) - timedelta(
                    days=rng.randint(0, 20)
                )
                if paid_at < created_at:
                    paid_at = created_at + timedelta(days=rng.randint(0, 3))
                if paid_at > datetime.now(UTC):
                    paid_at = datetime.now(UTC)

            payment = AdvancePayment(
                business_id=business.id,
                period=period,
                period_months_count=rng.choice([1, 1, 2]),
                due_date=due_date,
                expected_amount=expected_amount,
                paid_amount=paid_amount,
                status=status,
                paid_at=paid_at,
                payment_method=rng.choice(list(PaymentMethod))
                if status in (AdvancePaymentStatus.PAID, AdvancePaymentStatus.PARTIAL)
                else None,
                annual_report_id=None,
                notes=rng.choice([None, "הוזן אוטומטית", "נדרש מעקב מול הבנק"]),
                created_at=created_at,
                updated_at=None,
            )
            db.add(payment)
            payments.append(payment)
            db.flush()
            if deadline and deadline.deadline_type == TaxDeadlineType.ADVANCE_PAYMENT:
                deadline.advance_payment_id = payment.id
    db.flush()
    return payments
