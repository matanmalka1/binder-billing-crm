"""Timeline computation for tax deadlines."""

from datetime import date

from app.clients.services.client_lookup import get_client_or_raise


_MILESTONE_LABELS: dict[str, str] = {
    "vat_bimonthly": 'הגשת דוח מע"מ דו-חודשי',
    "vat_monthly": 'הגשת דוח מע"מ חודשי',
    "advance_payment": "תשלום מקדמה",
    "annual_report": "הגשת דוח שנתי",
    "national_insurance": "תשלום ביטוח לאומי",
    "income_tax": "תשלום מס הכנסה",
    "standard": "מועד סטנדרטי",
    "extended": "מועד מורחב",
    "custom": "מועד מותאם",
}


def build_timeline(client_id: int, client_repo, deadline_repo) -> list[dict]:
    """Return deadlines sorted by due_date asc with days_remaining and milestone_label."""
    get_client_or_raise(client_repo, client_id)
    deadlines = deadline_repo.list_by_client(client_id)
    today = date.today()
    result = []
    for d in sorted(deadlines, key=lambda x: x.due_date):
        days_remaining = (d.due_date - today).days
        deadline_type_val = d.deadline_type.value if hasattr(d.deadline_type, "value") else str(d.deadline_type)
        label = _MILESTONE_LABELS.get(deadline_type_val, deadline_type_val)
        result.append({
            "id": d.id,
            "client_id": d.client_id,
            "deadline_type": deadline_type_val,
            "due_date": d.due_date,
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "days_remaining": days_remaining,
            "milestone_label": label,
            "payment_amount": float(d.payment_amount) if d.payment_amount is not None else None,
        })
    return result
