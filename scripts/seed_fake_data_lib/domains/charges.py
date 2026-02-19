from __future__ import annotations

from datetime import UTC, datetime, timedelta, date
from decimal import Decimal
from random import Random

from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.invoice.models.invoice import Invoice


def create_charges(db, rng: Random, cfg, clients) -> list[Charge]:
    charges: list[Charge] = []
    for client in clients:
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
            paid_at = None
            if status in (ChargeStatus.ISSUED, ChargeStatus.PAID):
                issued_at = created_at + timedelta(days=rng.randint(0, 6))
            if status == ChargeStatus.PAID:
                paid_at = issued_at + timedelta(days=rng.randint(0, 20))

            charge_type = rng.choice(list(ChargeType))
            period = None
            if charge_type == ChargeType.RETAINER:
                month = rng.randint(1, 12)
                year = date.today().year - rng.randint(0, 1)
                period = f"{year}-{month:02d}"

            amount = Decimal(str(round(rng.uniform(250, 7500), 2)))
            charge = Charge(
                client_id=client.id,
                amount=amount,
                currency="ILS",
                charge_type=charge_type,
                period=period,
                status=status,
                created_at=created_at,
                issued_at=issued_at,
                paid_at=paid_at,
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
        invoice = Invoice(
            charge_id=charge.id,
            provider="demo-provider",
            external_invoice_id=f"INV-{invoice_serial}",
            document_url=f"https://example.local/invoices/INV-{invoice_serial}.pdf",
            issued_at=charge.issued_at or charge.created_at,
            created_at=charge.created_at,
        )
        invoice_serial += 1
        db.add(invoice)
    db.flush()
