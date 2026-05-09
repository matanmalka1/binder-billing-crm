from datetime import date
from decimal import Decimal, InvalidOperation

CHARGE_TYPE_LABELS = {
    "monthly_retainer": "ריטיינר חודשי",
    "annual_report_fee": "שכר טרחה לדוח שנתי",
    "vat_filing_fee": "שכר טרחה לדוח מע״מ",
    "representation_fee": "שכר טרחה לייצוג",
    "consultation_fee": "שכר טרחה לייעוץ",
    "other": "אחר",
}


def _format_ils_amount(amount) -> str:
    try:
        normalized = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        normalized = Decimal("0.00")
    if not normalized.is_finite():
        normalized = Decimal("0.00")
    formatted = f"{normalized:,.2f}".rstrip("0").rstrip(".")
    return f"₪{formatted}"


def _charge_type_label(charge_type) -> str:
    value = getattr(charge_type, "value", charge_type)
    return CHARGE_TYPE_LABELS.get(value, "חיוב")


def _charge_date(charge) -> date | None:
    timestamp = getattr(charge, "issued_at", None) or getattr(
        charge, "created_at", None
    )
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
    subject = _charge_subject(charge, business_name)
    hidden_parts = {business_name}
    client_name = getattr(charge, "_dashboard_client_name", None)
    if client_name:
        hidden_parts.add(client_name)
    for hidden in hidden_parts:
        subject = subject.replace(f" | {hidden}", "").replace(f"{hidden} | ", "")
    parts = [
        f"חשבונית #{_invoice_number(charge)}",
        subject,
    ]
    period = _period_label(getattr(charge, "period", None))
    if period:
        parts.append(f"תקופה {period}")
    return " · ".join(parts)


def unpaid_charge_attention_item(
    charge,
    business,
    client_display_name: str = "",
    reference_date: date | None = None,
) -> dict:
    reference_date = reference_date or date.today()
    business_name = (
        getattr(business, "business_name", None)
        or getattr(business, "full_name", None)
        or client_display_name
    )
    setattr(charge, "_dashboard_client_name", client_display_name)
    amount = _format_ils_amount(charge.amount)
    status_label = _charge_status_label(charge, reference_date)
    description_parts = [amount, status_label]
    if business_name and business_name != client_display_name:
        description_parts.insert(0, business_name)
    return {
        "item_type": "unpaid_charge",
        "charge_id": charge.id,
        "binder_id": None,
        "client_id": charge.client_record_id,
        "business_id": getattr(business, "id", None),
        "client_name": client_display_name,
        "business_name": business_name,
        "description": " · ".join(description_parts),
        "charge_subject": _charge_detail_line(charge, business_name),
        "charge_date": _charge_date(charge),
        "charge_amount": amount,
        "charge_invoice_number": _invoice_number(charge),
        "charge_period": getattr(charge, "period", None),
    }
