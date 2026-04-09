from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from random import Random

from app.businesses.models.business import BusinessStatus
from app.users.models.user import UserRole
from app.vat_reports.models.vat_audit_log import VatAuditLog
from app.vat_reports.models.vat_enums import (
    CounterpartyIdType,
    DocumentType,
    ExpenseCategory,
    InvoiceType,
    VatRateType,
    VatWorkItemStatus,
)
from app.vat_reports.models.vat_invoice import VatInvoice
from app.vat_reports.models.vat_work_item import VatWorkItem

from ._business_groups import group_businesses_by_client
from app.common.enums import VatType
from app.annual_reports.models.annual_report_enums import SubmissionMethod
from ..random_utils import generate_valid_israeli_id

DEDUCTION_RATES: dict[ExpenseCategory, Decimal] = {
    ExpenseCategory.TRAVEL: Decimal("0.6667"),
    ExpenseCategory.VEHICLE: Decimal("0.6667"),
    ExpenseCategory.FUEL: Decimal("0.6667"),
    ExpenseCategory.VEHICLE_MAINTENANCE: Decimal("0.6667"),
    ExpenseCategory.VEHICLE_LEASING: Decimal("0.6667"),
    ExpenseCategory.TOLLS_AND_PARKING: Decimal("0.6667"),
    ExpenseCategory.COMMUNICATION: Decimal("0.6667"),
    ExpenseCategory.MIXED_EXPENSE: Decimal("0.6667"),
    ExpenseCategory.SALARY: Decimal("0.0000"),
    ExpenseCategory.INSURANCE: Decimal("0.0000"),
    ExpenseCategory.ENTERTAINMENT: Decimal("0.0000"),
    ExpenseCategory.GIFTS: Decimal("0.0000"),
    ExpenseCategory.MUNICIPAL_TAX: Decimal("0.0000"),
}


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


def create_vat_work_items(db, rng: Random, cfg, businesses, users, profiles=None) -> list[VatWorkItem]:
    advisors = [u.id for u in users if u.role == UserRole.ADVISOR]
    fallback_user_id = users[0].id if users else None
    work_items: list[VatWorkItem] = []

    for client_businesses in group_businesses_by_client(businesses).values():
        eligible_businesses = [
            business
            for business in client_businesses
            if business.client.vat_reporting_frequency in (VatType.MONTHLY, VatType.BIMONTHLY)
        ]
        if not eligible_businesses:
            continue
        num_items = rng.randint(cfg.min_vat_work_items_per_client, cfg.max_vat_work_items_per_client)
        periods = _choose_periods(rng, num_items)

        for period in periods:
            business = rng.choice(eligible_businesses)
            period_start = datetime.strptime(f"{period}-01", "%Y-%m-%d").replace(tzinfo=UTC)
            created_at = max(
                period_start,
                datetime.now(UTC) - timedelta(days=rng.randint(5, 75)),
            )
            if created_at > datetime.now(UTC):
                created_at = datetime.now(UTC)
            period_type = business.client.vat_reporting_frequency
            if business.status == BusinessStatus.CLOSED:
                status = rng.choice([VatWorkItemStatus.FILED, VatWorkItemStatus.READY_FOR_REVIEW])
            elif business.status == BusinessStatus.FROZEN:
                status = rng.choice([
                    VatWorkItemStatus.PENDING_MATERIALS,
                    VatWorkItemStatus.MATERIAL_RECEIVED,
                    VatWorkItemStatus.READY_FOR_REVIEW,
                ])
            else:
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
                client_id=business.client_id,
                created_by=created_by,
                assigned_to=rng.choice(advisors) if advisors and rng.random() < 0.7 else None,
                period=period,
                period_type=period_type,
                status=status,
                created_at=created_at,
                updated_at=created_at,
                pending_materials_note="ממתינים לחשבוניות מהלקוח"
                if status == VatWorkItemStatus.PENDING_MATERIALS and rng.random() < 0.5
                else None,
            )

            if status == VatWorkItemStatus.FILED:
                work_item.submission_method = rng.choice(list(SubmissionMethod))
                filed_at_candidate = max(created_at, datetime.now(UTC) - timedelta(days=rng.randint(1, 90)))
                work_item.filed_at = min(datetime.now(UTC), filed_at_candidate)
                work_item.filed_by = work_item.assigned_to or work_item.created_by
                work_item.submission_reference = f"VAT-{work_item.period.replace('-', '')}-{rng.randint(1000, 9999)}"

            db.add(work_item)
            work_items.append(work_item)

    db.flush()

    filed_by_client: dict[int, list[VatWorkItem]] = defaultdict(list)
    for work_item in work_items:
        if work_item.status == VatWorkItemStatus.FILED:
            filed_by_client[work_item.client_id].append(work_item)

    for filed_items in filed_by_client.values():
        filed_items.sort(key=lambda item: item.period)
        for index in range(1, len(filed_items)):
            if rng.random() < 0.2:
                filed_items[index].is_amendment = True
                filed_items[index].amends_item_id = filed_items[index - 1].id
                filed_items[index].submission_reference = (
                    f"{filed_items[index].submission_reference or f'VAT-{filed_items[index].period.replace('-', '')}-{rng.randint(1000, 9999)}'}-AMD"
                )

    if not any(item.is_amendment for item in work_items):
        amendment_candidates = [
            filed_items
            for filed_items in filed_by_client.values()
            if len(filed_items) >= 2
        ]
        if amendment_candidates:
            filed_items = rng.choice(amendment_candidates)
            amended_item = filed_items[-1]
            source_item = filed_items[-2]
            amended_item.is_amendment = True
            amended_item.amends_item_id = source_item.id
            amended_item.submission_reference = (
                f"{amended_item.submission_reference or f'VAT-{amended_item.period.replace('-', '')}-{rng.randint(1000, 9999)}'}-AMD"
            )
    return work_items


def create_vat_invoices(db, rng: Random, cfg, work_items, users) -> list[VatInvoice]:
    invoices: list[VatInvoice] = []
    totals = defaultdict(lambda: {"output": Decimal("0.00"), "input": Decimal("0.00")})
    invoice_counters = defaultdict(int)

    for work_item in work_items:
        num_invoices = rng.randint(cfg.min_vat_invoices_per_work_item, cfg.max_vat_invoices_per_work_item)
        for _ in range(num_invoices):
            invoice_type = rng.choice(list(InvoiceType))
            base_amount = Decimal(str(round(rng.uniform(250, 30000), 2)))
            if invoice_type == InvoiceType.EXPENSE:
                expense_category = rng.choice(list(ExpenseCategory))
                document_type = rng.choice(
                    [
                        DocumentType.TAX_INVOICE,
                        DocumentType.TRANSACTION_INVOICE,
                        DocumentType.RECEIPT,
                        DocumentType.CONSOLIDATED,
                        DocumentType.SELF_INVOICE,
                    ]
                )
                deduction_rate = DEDUCTION_RATES.get(expense_category, Decimal("1.0000"))
            else:
                expense_category = None
                document_type = rng.choice(
                    [
                        DocumentType.TAX_INVOICE,
                        DocumentType.TRANSACTION_INVOICE,
                        DocumentType.RECEIPT,
                        DocumentType.CREDIT_NOTE,
                    ]
                )
                deduction_rate = Decimal("1.0000")

            rate_type = rng.choice([VatRateType.STANDARD, VatRateType.STANDARD, VatRateType.ZERO_RATE, VatRateType.EXEMPT])
            vat_amount = (
                Decimal("0.00")
                if rate_type in (VatRateType.ZERO_RATE, VatRateType.EXEMPT)
                else (base_amount * Decimal("0.18")).quantize(Decimal("0.01"))
            )

            invoice_counters[work_item.id] += 1
            invoice_number = f"{work_item.period.replace('-', '')}-{invoice_counters[work_item.id]:03d}"
            counterparty_id_type = (
                CounterpartyIdType.IL_BUSINESS
                if document_type == DocumentType.TAX_INVOICE
                else rng.choice([CounterpartyIdType.IL_BUSINESS, CounterpartyIdType.IL_PERSONAL, CounterpartyIdType.FOREIGN])
            )
            if counterparty_id_type == CounterpartyIdType.IL_BUSINESS:
                counterparty_id = generate_valid_israeli_id(
                    work_item.id * 1000 + invoice_counters[work_item.id],
                    prefix="5",
                )
            elif counterparty_id_type == CounterpartyIdType.IL_PERSONAL:
                counterparty_id = generate_valid_israeli_id(
                    work_item.id * 1000 + invoice_counters[work_item.id],
                    prefix=str(rng.choice([0, 1, 2, 3])),
                )
            else:
                counterparty_id = f"F{rng.randint(1000000, 9999999)}"

            invoice = VatInvoice(
                work_item_id=work_item.id,
                created_by=work_item.created_by or rng.choice(users).id,
                invoice_type=invoice_type,
                document_type=document_type,
                invoice_number=invoice_number,
                invoice_date=(datetime.now(UTC) - timedelta(days=rng.randint(1, 60))).date(),
                counterparty_name=rng.choice(["לקוח", "ספק", "סוכנות", "יבואן", "משווק"]) + f" {rng.randint(1, 999)}",
                counterparty_id=counterparty_id,
                counterparty_id_type=counterparty_id_type,
                net_amount=base_amount,
                vat_amount=vat_amount,
                expense_category=expense_category,
                rate_type=rate_type,
                deduction_rate=deduction_rate,
                is_exceptional=base_amount > Decimal("25000"),
            )
            db.add(invoice)
            invoices.append(invoice)

            if invoice_type == InvoiceType.INCOME:
                totals[work_item.id]["output"] += vat_amount
            else:
                totals[work_item.id]["input"] += (vat_amount * deduction_rate).quantize(Decimal("0.01"))

    db.flush()

    # Update totals on work items and set final amounts when filed
    for work_item in work_items:
        output_vat = totals[work_item.id]["output"]
        input_vat = totals[work_item.id]["input"]
        work_item.total_output_vat = output_vat
        work_item.total_input_vat = input_vat
        work_item.net_vat = output_vat - input_vat
        work_item.total_output_net = Decimal("0.00")
        work_item.total_input_net = Decimal("0.00")
        for invoice in invoices:
            if invoice.work_item_id != work_item.id:
                continue
            if invoice.invoice_type == InvoiceType.INCOME:
                work_item.total_output_net += Decimal(invoice.net_amount)
            else:
                work_item.total_input_net += Decimal(invoice.net_amount)

        if work_item.status == VatWorkItemStatus.FILED:
            work_item.final_vat_amount = work_item.net_vat
            work_item.is_overridden = rng.random() < 0.1
            if work_item.is_overridden:
                work_item.override_justification = "התאמה ידנית לעיגול"

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
        if work_item.is_amendment and work_item.amends_item_id:
            events.append(("amendment_linked", str(work_item.amends_item_id), work_item.period))

        for action, old, new in events:
            log = VatAuditLog(
                work_item_id=work_item.id,
                performed_by=rng.choice(advisors) if advisors else fallback_user_id,
                action=action,
                old_value=old,
                new_value=new,
                note=(
                    "נדרש תיקון לדיווח קודם"
                    if action == "amendment_linked"
                    else ("בוצע override ידני" if action == "filed" and work_item.is_overridden else None)
                ),
                invoice_id=None,
            )
            db.add(log)
    db.flush()
