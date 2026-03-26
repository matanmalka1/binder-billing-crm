from __future__ import annotations

from datetime import UTC, datetime, timedelta, date
from decimal import Decimal
from random import Random

from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.invoice.models.invoice import Invoice


def create_charges(db, rng: Random, cfg, businesses, users=None) -> list[Charge]:
    charges: list[Charge] = []
    for business in businesses:
        num = rng.randint(
            cfg.min_charges_per_client,
            cfg.max_charges_per_client,
        )
        for _ in range(num):
            status = rng.choices(
                [ChargeStatus.DRAFT, ChargeStatus.ISSUED, ChargeStatus.PAID, ChargeStatus.CANCELED],
                weights=[20, 30, 40, 10],
                k=1,
            )[0]
            created_at = datetime.now(UTC) - timedelta(days=rng.randint(0, 240))
            issued_at = None
            issued_by = None
            paid_at = None
            paid_by = None
            if status in (ChargeStatus.ISSUED, ChargeStatus.PAID):
                issued_at = created_at + timedelta(days=rng.randint(0, 6))
                issued_by = rng.choice(users).id if users else None
            if status == ChargeStatus.PAID:
                paid_at = issued_at + timedelta(days=rng.randint(0, 20))
                paid_by = rng.choice(users).id if users else None

            charge_type = rng.choice(list(ChargeType))
            period = None
            months_covered = 1
            if charge_type == ChargeType.MONTHLY_RETAINER:
                month = rng.randint(1, 12)
                year = date.today().year - rng.randint(0, 1)
                period = f"{year}-{month:02d}"
            elif charge_type in (ChargeType.VAT_FILING_FEE, ChargeType.OTHER) and rng.random() < 0.4:
                month = rng.randint(1, 12)
                year = date.today().year - rng.randint(0, 1)
                period = f"{year}-{month:02d}"
                months_covered = rng.choice([1, 2])

            amount = Decimal(str(round(rng.uniform(250, 7500), 2)))
            canceled_at = None
            canceled_by = None
            if status == ChargeStatus.CANCELED:
                canceled_at = created_at + timedelta(days=rng.randint(1, 8))
                canceled_by = rng.choice(users).id if users else None

            charge = Charge(
                business_id=business.id,
                amount=amount,
                charge_type=charge_type,
                period=period,
                months_covered=months_covered,
                status=status,
                description=rng.choice(
                    [
                        None,
                        "חיוב שירות חודשי",
                        "חיוב עבודה נקודתית",
                        "התחשבנות תקופתית",
                    ]
                ),
                created_at=created_at,
                created_by=rng.choice(users).id if users else None,
                issued_at=issued_at,
                issued_by=issued_by,
                paid_at=paid_at,
                paid_by=paid_by,
                canceled_at=canceled_at,
                canceled_by=canceled_by,
            )
            db.add(charge)
            charges.append(charge)
    db.flush()
    return charges


def create_invoices(db, charges) -> None:
    invoice_serial = 70000
    for charge in charges:
        if charge.status not in (ChargeStatus.ISSUED, ChargeStatus.PAID):
            continue
        invoice_id = f"חשבונית-{invoice_serial}"
        invoice = Invoice(
            charge_id=charge.id,
            provider="ספק-דמו",
            external_invoice_id=invoice_id,
            document_url=f"https://example.local/invoices/{invoice_id}.pdf",
            issued_at=charge.issued_at or charge.created_at,
            created_at=charge.created_at,
        )
        invoice_serial += 1
        db.add(invoice)
    db.flush()
