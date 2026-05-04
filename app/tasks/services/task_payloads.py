from datetime import date, datetime
from decimal import Decimal
from typing import Any


def _date_value(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


def _money(value: Any) -> str | None:
    if value is None:
        return None
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def tax_deadline_payload(deadline) -> dict[str, Any]:
    return {
        "deadline_type": _enum_value(deadline.deadline_type),
        "period": deadline.period,
        "tax_year": deadline.tax_year,
        "due_date": _date_value(deadline.due_date),
        "status": _enum_value(deadline.status),
    }


def vat_work_item_payload(item, due_date: date) -> dict[str, Any]:
    return {
        "period": item.period,
        "due_date": _date_value(due_date),
        "status": _enum_value(item.status),

    }


def annual_report_payload(report) -> dict[str, Any]:
    return {
        "tax_year": report.tax_year,
        "filing_deadline": _date_value(report.filing_deadline),
        "status": _enum_value(report.status),
    }


def advance_payment_payload(payment) -> dict[str, Any]:
    expected = payment.expected_amount
    paid = payment.paid_amount
    remaining = None
    if expected is not None:
        remaining = max(Decimal(str(expected)) - Decimal(str(paid or 0)), Decimal("0"))
    return {
        "period": payment.period,
        "period_months_count": payment.period_months_count,
        "due_date": _date_value(payment.due_date),
        "status": _enum_value(payment.status),
        "expected_amount": _money(expected),
        "paid_amount": _money(paid),
        "remaining_amount": _money(remaining),
        "payment_method": _enum_value(payment.payment_method),
        "paid_at": _date_value(payment.paid_at),
        "annual_report_id": payment.annual_report_id,
    }


def unpaid_charge_payload(charge, due_date: date) -> dict[str, Any]:
    return {
        "business_id": charge.business_id,
        "charge_type": _enum_value(charge.charge_type),
        "status": _enum_value(charge.status),
        "amount": _money(charge.amount),
        "issued_at": _date_value(charge.issued_at),
        "due_date": _date_value(due_date),
        "period": charge.period,
    }
