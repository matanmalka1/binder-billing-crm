from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from random import Random

from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.tax_deadline.models.tax_deadline import TaxDeadline, DeadlineType as TaxDeadlineType


def create_tax_deadlines(db, rng: Random, cfg, clients) -> list[TaxDeadline]:
    deadlines: list[TaxDeadline] = []
    today = date.today()
    for client in clients:
        num = rng.randint(
            cfg.min_tax_deadlines_per_client,
            cfg.max_tax_deadlines_per_client,
        )
        for _ in range(num):
            due_offset = rng.randint(-30, 60)
            due_date = today + timedelta(days=due_offset)
            status = "completed" if due_date < today and rng.random() < 0.5 else "pending"
            completed_at = (
                datetime.now(UTC) - timedelta(days=rng.randint(1, 30))
                if status == "completed"
                else None
            )
            payment_amount = Decimal(str(round(rng.uniform(500, 15000), 2)))
            deadline_type = rng.choice(list(TaxDeadlineType))
            description = f"{deadline_type.value.replace('_', ' ').title()} reminder"
            deadline = TaxDeadline(
                client_id=client.id,
                deadline_type=deadline_type,
                due_date=due_date,
                status=status,
                payment_amount=payment_amount,
                currency="ILS",
                description=description,
                created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 120)),
                completed_at=completed_at,
            )
            db.add(deadline)
            deadlines.append(deadline)
    db.flush()
    return deadlines


def create_advance_payments(db, rng: Random, clients, deadlines) -> list[AdvancePayment]:
    payments: list[AdvancePayment] = []
    deadlines_by_client_month = {}
    for dl in deadlines:
        key = (dl.client_id, dl.due_date.year, dl.due_date.month)
        deadlines_by_client_month[key] = dl

    for client in clients:
        year = date.today().year
        months = rng.sample(range(1, 13), k=rng.randint(3, 7))
        for month in months:
            due_date = date(year, month, rng.randint(10, 28))
            deadline = deadlines_by_client_month.get((client.id, year, month))
            status = rng.choice(list(AdvancePaymentStatus))
            expected_amount = Decimal(str(round(rng.uniform(500, 6000), 2)))
            paid_amount = None
            if status in (AdvancePaymentStatus.PAID, AdvancePaymentStatus.PARTIAL):
                paid_amount = Decimal(str(round(rng.uniform(200, float(expected_amount)), 2)))

            payment = AdvancePayment(
                client_id=client.id,
                tax_deadline_id=deadline.id if deadline else None,
                month=month,
                year=year,
                expected_amount=expected_amount,
                paid_amount=paid_amount,
                status=status,
                due_date=due_date,
                created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 200)),
                updated_at=None,
            )
            db.add(payment)
            payments.append(payment)
    db.flush()
    return payments
