from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from random import Random

from app.advance_payments.models.advance_payment import (
    AdvancePayment,
    AdvancePaymentStatus,
    PaymentMethod,
)
from app.common.enums import EntityType, ObligationType
from app.common.obligation_plan import advance_payment_obligation_plan
from app.tax_calendar.services.materialization_service import (
    TaxCalendarMaterializationService,
)

from ..shared.client_refs import get_seed_client_record, get_seed_client_record_id

_HISTORICAL_YEARS = 3


def _resolve_status(period: str, current_year: int) -> AdvancePaymentStatus:
    period_year = int(period.split("-")[0])
    if period_year < current_year:
        return AdvancePaymentStatus.PAID
    return AdvancePaymentStatus.PENDING


def _apply_payment_fields(
    rng: Random, payment: AdvancePayment, status: AdvancePaymentStatus, period: str
) -> None:
    payment.status = status
    if status == AdvancePaymentStatus.PAID:
        payment.paid_amount = payment.expected_amount or Decimal(str(round(rng.uniform(500, 8_000), 2)))
        payment.payment_method = rng.choice(list(PaymentMethod))
        period_dt = datetime.strptime(f"{period}-01", "%Y-%m-%d").replace(tzinfo=UTC)
        paid_at = period_dt + timedelta(days=rng.randint(14, 45))
        payment.paid_at = min(paid_at, datetime.now(UTC))
    elif status == AdvancePaymentStatus.PARTIAL:
        expected = payment.expected_amount or Decimal(str(round(rng.uniform(500, 8_000), 2)))
        payment.paid_amount = (
            expected * Decimal(str(round(rng.uniform(0.2, 0.8), 2)))
        ).quantize(Decimal("0.01"))
        payment.payment_method = rng.choice(list(PaymentMethod))
        period_dt = datetime.strptime(f"{period}-01", "%Y-%m-%d").replace(tzinfo=UTC)
        paid_at = period_dt + timedelta(days=rng.randint(14, 45))
        payment.paid_at = min(paid_at, datetime.now(UTC))
    else:
        payment.paid_amount = Decimal("0.00")
        payment.payment_method = None
        payment.paid_at = None


def create_advance_payments(
    db, rng: Random, cfg, businesses
) -> list[AdvancePayment]:
    current_year = cfg.reference_date.year
    historical_years = list(range(current_year - _HISTORICAL_YEARS, current_year))
    mat = TaxCalendarMaterializationService(db)
    payments: list[AdvancePayment] = []

    seen_clients: set[int] = set()
    for business in businesses:
        cr = get_seed_client_record(business)
        if cr is None:
            continue
        client_record_id = get_seed_client_record_id(business)
        if client_record_id in seen_clients:
            continue
        seen_clients.add(client_record_id)

        frequency = getattr(cr, "advance_payment_frequency", None)
        entity_type = getattr(cr, "entity_type", None)
        if frequency is None or entity_type == EntityType.EMPLOYEE:
            continue

        for year in historical_years:
            plans = advance_payment_obligation_plan(
                frequency=frequency,
                year=year,
                entity_type=entity_type,
            )
            for plan in plans:
                existing = (
                    db.query(AdvancePayment)
                    .filter(
                        AdvancePayment.client_record_id == client_record_id,
                        AdvancePayment.period == plan.period,
                        AdvancePayment.deleted_at.is_(None),
                    )
                    .first()
                )
                status = _resolve_status(plan.period, current_year)

                if existing:
                    _apply_payment_fields(rng, existing, status, plan.period)
                    payments.append(existing)
                    continue

                entry = mat.ensure_periodic_entry(
                    ObligationType.ADVANCE_PAYMENT,
                    plan.period,
                    plan.period_months_count,
                )
                expected = Decimal(str(round(rng.uniform(500, 8_000), 2)))
                payment = AdvancePayment(
                    client_record_id=client_record_id,
                    period=plan.period,
                    period_months_count=plan.period_months_count,
                    due_date=entry.due_date,
                    due_date_original=entry.due_date,
                    due_date_effective=entry.due_date,
                    expected_amount=expected,
                    paid_amount=Decimal("0.00"),
                    status=AdvancePaymentStatus.PENDING,
                    tax_calendar_entry_id=entry.id,
                )
                _apply_payment_fields(rng, payment, status, plan.period)
                db.add(payment)
                payments.append(payment)

    db.flush()

    # Sweep: fix any remaining PENDING payments from onboarding not reached above.
    db.expire_all()
    stragglers = (
        db.query(AdvancePayment)
        .filter(
            AdvancePayment.period < f"{current_year}-01",
            AdvancePayment.status == AdvancePaymentStatus.PENDING,
            AdvancePayment.deleted_at.is_(None),
        )
        .all()
    )
    for p in stragglers:
        status = _resolve_status(p.period, current_year)
        _apply_payment_fields(rng, p, status, p.period)

    db.flush()
    return payments
