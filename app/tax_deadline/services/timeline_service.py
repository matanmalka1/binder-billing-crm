"""Timeline computation for tax deadlines."""

from datetime import date

from app.core.exceptions import NotFoundError


_MILESTONE_LABELS: dict[str, str] = {
    "vat":                'הגשת דוח מע"מ',
    "advance_payment":    "תשלום מקדמה",
    "annual_report":      "הגשת דוח שנתי",
    "national_insurance": "תשלום ביטוח לאומי",
    "other":              "מועד אחר",
}


def build_timeline(client_id: int, client_repo, deadline_repo) -> list[dict]:
    """Return deadlines sorted by due_date asc with days_remaining and milestone_label."""
    client = client_repo.get_by_id(client_id)
    if not client:
        raise NotFoundError(f"לקוח {client_id} לא נמצא", "CLIENT.NOT_FOUND")
    deadlines = deadline_repo.list_by_client(client_id)
    today = date.today()
    result = []
    for d in sorted(deadlines, key=lambda x: x.due_date):
        days_remaining = (d.due_date - today).days
        label = _MILESTONE_LABELS.get(d.deadline_type.value, d.deadline_type.value)
        result.append({
            "id": d.id,
            "client_id": d.client_id,
            "deadline_type": d.deadline_type,
            "period": d.period,
            "due_date": d.due_date,
            "status": d.status,
            "days_remaining": days_remaining,
            "milestone_label": label,
            "payment_amount": d.payment_amount,
        })
    return result
