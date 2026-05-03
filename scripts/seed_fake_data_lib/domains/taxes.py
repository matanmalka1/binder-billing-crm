from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from random import Random

from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus, PaymentMethod
from app.annual_reports.services.deadlines import standard_deadline
from app.clients.constants import ENTITY_TYPE_TO_REPORT_CLIENT_TYPE
from app.common.enums import EntityType
from app.tax_deadline.models.tax_deadline import (
    TaxDeadline,
    DeadlineType as TaxDeadlineType,
    TaxDeadlineStatus,
)
from app.tax_deadline.services.due_date_rules import periodic_due_date

from ._business_groups import group_businesses_by_client, pick_businesses_for_client


# Hebrew labels for deadline types used in seed descriptions
DEADLINE_LABELS = {
    TaxDeadlineType.ADVANCE_PAYMENT: "מקדמה",
    TaxDeadlineType.ANNUAL_REPORT: "דוח שנתי",
    TaxDeadlineType.NATIONAL_INSURANCE: "ביטוח לאומי",
    TaxDeadlineType.VAT: 'מע"מ',
}


def _eligible_deadline_types(business) -> list[TaxDeadlineType]:
    # ANNUAL_REPORT excluded — created separately via _create_annual_report_deadlines
    # ADVANCE_PAYMENT excluded — created via create_advance_payments
    # VAT deadlines are created from VatWorkItem history so links stay consistent.
    return [TaxDeadlineType.NATIONAL_INSURANCE]


def create_tax_deadlines(db, rng: Random, cfg, businesses, users=None) -> list[TaxDeadline]:
    deadlines: list[TaxDeadline] = []
    used_period_identities: set[tuple[int, TaxDeadlineType, str]] = set()
    today = cfg.reference_date
    for client_businesses in group_businesses_by_client(businesses).values():
        num = rng.randint(
            cfg.min_tax_deadlines_per_client,
            cfg.max_tax_deadlines_per_client,
        )
        for business in pick_businesses_for_client(rng, client_businesses, num):
            due_date, deadline_type, period = _pick_unique_deadline_identity(
                rng,
                today,
                business,
                used_period_identities,
            )
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
            description = f"תזכורת עבור {DEADLINE_LABELS.get(deadline_type, 'מועד מס')}"
            deadline = TaxDeadline(
                client_record_id=business.client_id,
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
            deadline.client_id = business.client_id
            db.add(deadline)
            deadlines.append(deadline)
    db.flush()
    _create_annual_report_deadlines(db, deadlines, businesses, cfg)
    _ensure_deadline_type_coverage(db, deadlines, businesses, users, rng)
    _ensure_overdue_deadline_coverage(db, deadlines, businesses, rng)
    return deadlines


def _create_annual_report_deadlines(db, deadlines: list, businesses, cfg) -> None:
    """Create one annual_report deadline per client using the statutory deadline."""
    year = cfg.reference_date.year
    seen_clients: set[int] = set()
    for business in businesses:
        cid = business.client_id
        if cid in seen_clients:
            continue
        seen_clients.add(cid)
        client = business.client
        exists = (
            db.query(TaxDeadline)
            .filter(
                TaxDeadline.client_record_id == cid,
                TaxDeadline.deadline_type == TaxDeadlineType.ANNUAL_REPORT,
                TaxDeadline.tax_year == year,
                TaxDeadline.deleted_at.is_(None),
            )
            .first()
        )
        if exists:
            continue
        client_type = ENTITY_TYPE_TO_REPORT_CLIENT_TYPE.get(
            getattr(client, "entity_type", None)
        )
        due_date = standard_deadline(year, client_type=client_type).date()
        deadline = TaxDeadline(
            client_record_id=cid,
            deadline_type=TaxDeadlineType.ANNUAL_REPORT,
            tax_year=year,
            due_date=due_date,
            status=TaxDeadlineStatus.PENDING,
            description=f"דוח שנתי שנת {year}",
            created_at=datetime.now(UTC),
        )
        deadline.client_id = cid
        db.add(deadline)
        deadlines.append(deadline)
    db.flush()


def _pick_unique_deadline_identity(
    rng: Random,
    today: date,
    business,
    used_period_identities: set[tuple[int, TaxDeadlineType, str]],
) -> tuple[date, TaxDeadlineType, str | None]:
    deadline_type = rng.choice(_eligible_deadline_types(business))
    for month_offset in range(-1, 25):
        anchor = _add_months(today, month_offset)
        due_date = _statutory_due_date(deadline_type, anchor)
        period = f"{due_date.year}-{due_date.month:02d}"
        identity = (business.client_id, deadline_type, period)
        if identity not in used_period_identities:
            used_period_identities.add(identity)
            return due_date, deadline_type, period
    return (
        today,
        TaxDeadlineType.NATIONAL_INSURANCE,
        f"{today.year}-{today.month:02d}",
    )


def _statutory_due_date(deadline_type: TaxDeadlineType, anchor: date) -> date:
    """Return the correct statutory due date for a deadline type given a month anchor."""
    from app.tax_deadline.services.constants import ADVANCE_PAYMENT_DUE_DAY
    from app.vat_reports.services.constants import VAT_STATUTORY_DEADLINE_DAY

    if deadline_type == TaxDeadlineType.VAT:
        filing_month = anchor.month + 1 if anchor.month < 12 else 1
        filing_year = anchor.year if anchor.month < 12 else anchor.year + 1
        return date(filing_year, filing_month, VAT_STATUTORY_DEADLINE_DAY)
    if deadline_type == TaxDeadlineType.ADVANCE_PAYMENT:
        return date(anchor.year, anchor.month, ADVANCE_PAYMENT_DUE_DAY)
    # NATIONAL_INSURANCE: 15th of month (approximation — no statutory formula in system)
    return date(anchor.year, anchor.month, 15)


def _add_months(value: date, month_offset: int) -> date:
    month_index = value.month - 1 + month_offset
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _ensure_deadline_type_coverage(db, deadlines, businesses, users, rng) -> None:
    present = {d.deadline_type for d in deadlines}
    # VAT, ADVANCE_PAYMENT and ANNUAL_REPORT are seeded from their domain records.
    required = [TaxDeadlineType.NATIONAL_INSURANCE]
    missing = [t for t in required if t not in present]
    if missing:
        today = date.today()
        fallback_business = businesses[0]
        for dtype in missing:
            anchor = _add_months(today, 1)
            due_date = _statutory_due_date(dtype, anchor)
            period = f"{due_date.year}-{due_date.month:02d}"
            deadline = TaxDeadline(
                client_record_id=fallback_business.client_id,
                deadline_type=dtype,
                period=period,
                due_date=due_date,
                status=TaxDeadlineStatus.PENDING,
                payment_amount=Decimal("1000.00"),
                description=f"תזכורת עבור {DEADLINE_LABELS.get(dtype, 'מועד מס')}",
                created_at=datetime.now(UTC),
            )
            deadline.client_id = fallback_business.client_id
            db.add(deadline)
            deadlines.append(deadline)
        db.flush()

    _ensure_upcoming_window_coverage(db, deadlines, businesses)

    present_statuses = {deadline.status for deadline in deadlines}
    if TaxDeadlineStatus.CANCELED not in present_statuses and deadlines:
        canceled_deadline = deadlines[0]
        canceled_deadline.status = TaxDeadlineStatus.CANCELED
        canceled_deadline.completed_at = None
        canceled_deadline.completed_by = None


def _ensure_upcoming_window_coverage(db, deadlines: list, businesses) -> None:
    """Guarantee at least one PENDING deadline of each type within the next 14 days."""
    today = date.today()
    window_end = _add_months(today, 1)
    present_in_window = {
        d.deadline_type
        for d in deadlines
        if d.status == TaxDeadlineStatus.PENDING and today <= d.due_date <= window_end
    }
    needed = [TaxDeadlineType.NATIONAL_INSURANCE]
    fallback_business = businesses[0]
    existing_periods = {
        (d.client_record_id, d.deadline_type, d.period)
        for d in deadlines
        if d.period
    }
    for dtype in needed:
        if dtype in present_in_window:
            continue
        # Find the next statutory due_date on or after today
        for offset in range(0, 3):
            anchor = _add_months(today, offset)
            due_date = _statutory_due_date(dtype, anchor)
            if due_date < today:
                continue
            period = f"{due_date.year}-{due_date.month:02d}"
            if (fallback_business.client_id, dtype, period) in existing_periods:
                continue
            dl = TaxDeadline(
                client_record_id=fallback_business.client_id,
                deadline_type=dtype,
                period=period,
                due_date=due_date,
                status=TaxDeadlineStatus.PENDING,
                payment_amount=Decimal("1000.00"),
                description=f"תזכורת עבור {DEADLINE_LABELS.get(dtype, 'מועד מס')}",
                created_at=datetime.now(UTC),
            )
            dl.client_id = fallback_business.client_id
            db.add(dl)
            deadlines.append(dl)
            break
    db.flush()


def _ensure_overdue_deadline_coverage(db, deadlines: list, businesses, rng: Random) -> None:
    """Guarantee at least 3 PENDING deadlines with due_date in the past (triggers OVERDUE urgency)."""
    today = date.today()
    overdue_count = sum(
        1 for d in deadlines
        if d.status == TaxDeadlineStatus.PENDING and d.due_date < today
    )
    needed = max(0, 3 - overdue_count)
    if needed == 0:
        return
    used_clients = set()
    for business in businesses:
        if needed == 0:
            break
        cid = business.client_id
        if cid in used_clients:
            continue
        used_clients.add(cid)
        dtype = TaxDeadlineType.NATIONAL_INSURANCE
        days_overdue = rng.randint(5, 45)
        due_date = today - timedelta(days=days_overdue)
        period = f"{due_date.year}-{due_date.month:02d}"
        dl = TaxDeadline(
            client_record_id=cid,
            deadline_type=dtype,
            period=period,
            due_date=due_date,
            status=TaxDeadlineStatus.PENDING,
            payment_amount=Decimal(str(round(rng.uniform(500, 8000), 2))),
            description=f"תזכורת עבור {DEADLINE_LABELS[dtype]} - באיחור",
            created_at=datetime.now(UTC) - timedelta(days=days_overdue + rng.randint(5, 20)),
        )
        dl.client_id = cid
        db.add(dl)
        deadlines.append(dl)
        needed -= 1
    db.flush()


def create_advance_payments(db, rng: Random, cfg, businesses, deadlines) -> list[AdvancePayment]:
    payments: list[AdvancePayment] = []
    eligible_businesses = [
        business for business in businesses if business.client.entity_type != EntityType.EMPLOYEE
    ]
    deadlines_by_client_period = {}
    for dl in deadlines:
        if dl.period and dl.deadline_type == TaxDeadlineType.ADVANCE_PAYMENT:
            deadlines_by_client_period[(dl.client_id, dl.period)] = dl

    for client_businesses in group_businesses_by_client(eligible_businesses).values():
        periods = _historical_month_periods(
            rng,
            cfg_reference_date=cfg.reference_date,
            count=rng.randint(6, 12),
        )
        for period in periods:
            business = rng.choice(client_businesses)
            year, month = [int(part) for part in period.split("-")]
            due_date = periodic_due_date(year, month, period)
            existing_payment = (
                db.query(AdvancePayment)
                .filter(
                    AdvancePayment.client_record_id == business.client_id,
                    AdvancePayment.period == period,
                    AdvancePayment.deleted_at.is_(None),
                )
                .first()
            )
            if existing_payment is not None:
                continue
            deadline = deadlines_by_client_period.get((business.client_id, period))
            status = _advance_status_for_due_date(rng, due_date, cfg.reference_date)
            expected_amount = Decimal(str(round(rng.uniform(500, 6000), 2)))
            paid_amount = Decimal("0.00")
            if status in (AdvancePaymentStatus.PAID, AdvancePaymentStatus.PARTIAL):
                paid_amount = Decimal(str(round(rng.uniform(200, float(expected_amount)), 2)))
            if status == AdvancePaymentStatus.PAID:
                paid_amount = expected_amount
            elif status == AdvancePaymentStatus.PARTIAL:
                paid_amount = min(expected_amount - Decimal("1.00"), paid_amount)
                if paid_amount <= Decimal("0.00"):
                    paid_amount = (expected_amount * Decimal("0.5")).quantize(Decimal("0.01"))
            elif status == AdvancePaymentStatus.PENDING:
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
                client_record_id=business.client_id,
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
            payment.client_id = business.client_id
            db.add(payment)
            payments.append(payment)
            db.flush()
            if deadline is None:
                adv_deadline = TaxDeadline(
                    client_record_id=business.client_id,
                    deadline_type=TaxDeadlineType.ADVANCE_PAYMENT,
                    period=period,
                    due_date=due_date,
                    status=(
                        TaxDeadlineStatus.COMPLETED
                        if status in (AdvancePaymentStatus.PAID, AdvancePaymentStatus.PARTIAL)
                        else TaxDeadlineStatus.PENDING
                    ),
                    payment_amount=expected_amount,
                    description=f"מקדמה {period}",
                    created_at=created_at,
                    advance_payment_id=payment.id,
                )
                adv_deadline.client_id = business.client_id
                db.add(adv_deadline)
            elif deadline.advance_payment_id is None:
                deadline.advance_payment_id = payment.id
            db.flush()
    db.flush()
    return payments


def _historical_month_periods(rng: Random, cfg_reference_date: date, count: int) -> list[str]:
    periods = []
    cursor = cfg_reference_date.replace(day=1)
    for _ in range(count * 3):
        cursor = _add_months(cursor, -1)
        period = f"{cursor.year}-{cursor.month:02d}"
        if periodic_due_date(cursor.year, cursor.month, period) >= cfg_reference_date:
            continue
        if period not in periods:
            periods.append(period)
        if len(periods) >= count:
            break
    return sorted(periods)


def _advance_status_for_due_date(rng: Random, due_date: date, reference_date: date) -> AdvancePaymentStatus:
    age_days = (reference_date - due_date).days
    if age_days > 90:
        return rng.choices(
            [AdvancePaymentStatus.PAID, AdvancePaymentStatus.PARTIAL, AdvancePaymentStatus.PENDING],
            weights=[80, 15, 5],
            k=1,
        )[0]
    if age_days > 30:
        return rng.choices(
            [AdvancePaymentStatus.PAID, AdvancePaymentStatus.PARTIAL, AdvancePaymentStatus.PENDING],
            weights=[50, 25, 25],
            k=1,
        )[0]
    return rng.choices(
        [AdvancePaymentStatus.PAID, AdvancePaymentStatus.PARTIAL, AdvancePaymentStatus.PENDING],
        weights=[20, 20, 60],
        k=1,
    )[0]
