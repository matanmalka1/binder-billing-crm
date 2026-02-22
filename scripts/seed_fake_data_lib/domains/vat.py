from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from random import Random

from app.users.models.user import UserRole
from app.vat_reports.models.vat_audit_log import VatAuditLog
from app.vat_reports.models.vat_enums import (
    ExpenseCategory,
    FilingMethod,
    InvoiceType,
    VatWorkItemStatus,
)
from app.vat_reports.models.vat_invoice import VatInvoice
from app.vat_reports.models.vat_work_item import VatWorkItem


def _choose_periods(rng: Random, count: int) -> list[str]:
    """Return unique recent periods like '2026-01', most recent months first."""
    today = datetime.now(UTC)
    periods: list[str] = []
    for i in range(count * 2):
        candidate = (today - timedelta(days=30 * i)).strftime("%Y-%m")
        if candidate not in periods:
            periods.append(candidate)
        if len(periods) >= count:
            break
    return periods[:count]


def create_vat_work_items(db, rng: Random, cfg, clients, users) -> list[VatWorkItem]:
    advisors = [u.id for u in users if u.role == UserRole.ADVISOR]
    fallback_user_id = users[0].id if users else None
    work_items: list[VatWorkItem] = []

    for client in clients:
        num_items = rng.randint(cfg.min_vat_work_items_per_client, cfg.max_vat_work_items_per_client)
        periods = _choose_periods(rng, num_items)
        for period in periods:
            status = rng.choices(
                population=[
                    VatWorkItemStatus.PENDING_MATERIALS,
                    VatWorkItemStatus.MATERIAL_RECEIVED,
                    VatWorkItemStatus.DATA_ENTRY_IN_PROGRESS,
                    VatWorkItemStatus.READY_FOR_REVIEW,
                    VatWorkItemStatus.FILED,
                ],
                weights=[10, 25, 25, 20, 20],
                k=1,
            )[0]

            created_by = rng.choice(advisors) if advisors else fallback_user_id
            work_item = VatWorkItem(
                client_id=client.id,
                created_by=created_by,
                assigned_to=rng.choice(advisors) if advisors and rng.random() < 0.7 else None,
                period=period,
                status=status,
                pending_materials_note="Awaiting invoices from client"
                if status == VatWorkItemStatus.PENDING_MATERIALS and rng.random() < 0.5
                else None,
            )

            if status == VatWorkItemStatus.FILED:
                work_item.filing_method = rng.choice(list(FilingMethod))
                work_item.filed_at = datetime.now(UTC) - timedelta(days=rng.randint(1, 90))
                work_item.filed_by = work_item.assigned_to or work_item.created_by

            db.add(work_item)
            work_items.append(work_item)

    db.flush()
    return work_items


def create_vat_invoices(db, rng: Random, cfg, work_items, users) -> list[VatInvoice]:
    invoices: list[VatInvoice] = []
    totals = defaultdict(lambda: {"output": Decimal("0.00"), "input": Decimal("0.00")})
    invoice_counters = defaultdict(int)

    for work_item in work_items:
        num_invoices = rng.randint(cfg.min_vat_invoices_per_work_item, cfg.max_vat_invoices_per_work_item)
        for _ in range(num_invoices):
            invoice_type = rng.choice(list(InvoiceType))
            base_amount = Decimal(str(round(rng.uniform(250, 12000), 2)))
            vat_amount = (base_amount * Decimal("0.17")).quantize(Decimal("0.01"))

            invoice_counters[work_item.id] += 1
            invoice_number = f"{work_item.period.replace('-', '')}-{invoice_counters[work_item.id]:03d}"

            invoice = VatInvoice(
                work_item_id=work_item.id,
                created_by=work_item.created_by or rng.choice(users).id,
                invoice_type=invoice_type,
                invoice_number=invoice_number,
                invoice_date=datetime.now(UTC) - timedelta(days=rng.randint(1, 60)),
                counterparty_name=rng.choice(["Client", "Supplier", "Agency"]) + f" {rng.randint(1, 999)}",
                counterparty_id=str(rng.randint(100000000, 999999999)),
                net_amount=base_amount,
                vat_amount=vat_amount,
                expense_category=rng.choice(list(ExpenseCategory)) if invoice_type == InvoiceType.EXPENSE else None,
            )
            db.add(invoice)
            invoices.append(invoice)

            if invoice_type == InvoiceType.INCOME:
                totals[work_item.id]["output"] += vat_amount
            else:
                totals[work_item.id]["input"] += vat_amount

    db.flush()

    # Update totals on work items and set final amounts when filed
    for work_item in work_items:
        output_vat = totals[work_item.id]["output"]
        input_vat = totals[work_item.id]["input"]
        work_item.total_output_vat = output_vat
        work_item.total_input_vat = input_vat
        work_item.net_vat = output_vat - input_vat

        if work_item.status == VatWorkItemStatus.FILED:
            work_item.final_vat_amount = work_item.net_vat
            work_item.is_overridden = rng.random() < 0.1
            if work_item.is_overridden:
                work_item.override_justification = "Manual adjustment for rounding"

    db.flush()
    return invoices


def create_vat_audit_logs(db, rng: Random, work_items, users) -> None:
    advisors = [u.id for u in users if u.role == UserRole.ADVISOR]
    fallback_user_id = users[0].id if users else None
    for work_item in work_items:
        events = [
            ("status_changed", None, work_item.status.value),
        ]
        if work_item.net_vat:
            events.append(("vat_calculated", None, str(work_item.net_vat)))
        if work_item.filed_at:
            events.append(("filed", None, str(work_item.final_vat_amount or work_item.net_vat)))

        for action, old, new in events:
            log = VatAuditLog(
                work_item_id=work_item.id,
                performed_by=rng.choice(advisors) if advisors else fallback_user_id,
                action=action,
                old_value=old,
                new_value=new,
                note=None,
            )
            db.add(log)
    db.flush()
