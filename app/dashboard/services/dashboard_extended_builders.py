from datetime import date
from decimal import Decimal

CHARGE_TYPE_LABELS = {
    "monthly_retainer": "ריטיינר חודשי",
    "annual_report_fee": "שכר טרחה לדוח שנתי",
    "vat_filing_fee": "שכר טרחה לדוח מע״מ",
    "representation_fee": "שכר טרחה לייצוג",
    "consultation_fee": "שכר טרחה לייעוץ",
    "other": "אחר",
}


def _format_ils_amount(amount) -> str:
    normalized = Decimal(str(amount)).quantize(Decimal("0.01"))
    formatted = f"{normalized:,.2f}".rstrip("0").rstrip(".")
    return f"₪{formatted}"


def _charge_type_label(charge_type) -> str:
    value = getattr(charge_type, "value", charge_type)
    return CHARGE_TYPE_LABELS.get(value, "חיוב")


def _charge_date(charge) -> date | None:
    timestamp = getattr(charge, "issued_at", None) or getattr(charge, "created_at", None)
    if timestamp is None:
        return None
    return timestamp.date() if hasattr(timestamp, "date") else timestamp


def _charge_status_label(charge, reference_date: date) -> str:
    charge_date = _charge_date(charge)
    if charge_date is None:
        return "פתוח"
    days_overdue = (reference_date - charge_date).days
    if days_overdue <= 0:
        return "לתשלום היום"
    return f"באיחור {days_overdue} ימים"


def _period_label(period: str | None) -> str | None:
    if not period:
        return None
    try:
        year, month = period.split("-")
    except ValueError:
        return period
    return f"{month}/{year}"


def _invoice_number(charge) -> str:
    invoice = getattr(charge, "invoice", None)
    if invoice is not None and getattr(invoice, "id", None) is not None:
        return str(invoice.id)
    return str(charge.id)


def _charge_subject(charge, business_name: str) -> str:
    subject = getattr(charge, "description", None) or _charge_type_label(
        getattr(charge, "charge_type", None)
    )
    period = getattr(charge, "period", None)
    hidden_parts = {business_name}
    if period:
        hidden_parts.add(f"תקופה {period}")
    return " | ".join(part for part in subject.split(" | ") if part not in hidden_parts)


def _charge_detail_line(charge, business_name: str) -> str:
    parts = [
        f"חשבונית #{_invoice_number(charge)}",
        _charge_subject(charge, business_name),
    ]
    period = _period_label(getattr(charge, "period", None))
    if period:
        parts.append(f"תקופה {period}")
    return " · ".join(parts)


def ready_attention_item(binder, client) -> dict:
    return {
        "item_type": "ready_for_pickup",
        "binder_id": binder.id,
        "client_id": binder.client_record_id,
        "business_id": client.id,
        "client_name": client.full_name,
        "description": f"תיק {binder.binder_number} מוכן לאיסוף",
    }


def unpaid_charge_attention_item(
    charge,
    business,
    client_display_name: str = "",
    reference_date: date | None = None,
) -> dict:
    reference_date = reference_date or date.today()
    business_name = getattr(business, "business_name", getattr(business, "full_name", ""))
    amount = _format_ils_amount(charge.amount)
    return {
        "item_type": "unpaid_charge",
        "binder_id": None,
        "client_id": charge.client_record_id,
        "business_id": business.id,
        "client_name": client_display_name,
        "business_name": business_name,
        "description": f"{business_name} · {amount} · {_charge_status_label(charge, reference_date)}",
        "charge_subject": _charge_detail_line(charge, business_name),
        "charge_date": _charge_date(charge),
        "charge_amount": amount,
        "charge_invoice_number": _invoice_number(charge),
        "charge_period": getattr(charge, "period", None),
    }
