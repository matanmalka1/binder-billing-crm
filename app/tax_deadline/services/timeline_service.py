"""Timeline computation for tax deadlines."""

from datetime import date

from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.core.exceptions import NotFoundError
from app.tax_deadline.services.urgency import compute_deadline_urgency


_MILESTONE_LABELS: dict[str, str] = {
    "vat":                'הגשת דוח מע"מ',
    "advance_payment":    "תשלום מקדמה",
    "annual_report":      "הגשת דוח שנתי",
    "national_insurance": "תשלום ביטוח לאומי",
    "other":              "מועד אחר",
}


def build_timeline(client_record_id: int, db, deadline_repo) -> list[dict]:
    """Return deadlines sorted by due_date asc with days_remaining and milestone_label."""
    client_record = ClientRecordRepository(db).get_by_id(client_record_id)
    if not client_record:
        raise NotFoundError(f"רשומת לקוח {client_record_id} לא נמצאה", "CLIENT_RECORD.NOT_FOUND")
    deadlines = deadline_repo.list_by_client(client_record_id)
    today = date.today()
    result = []
    for d in sorted(deadlines, key=lambda x: x.due_date):
        days_remaining = (d.due_date - today).days
        label = _MILESTONE_LABELS.get(d.deadline_type.value, d.deadline_type.value)
        result.append({
            "id": d.id,
            "client_record_id": d.client_record_id,
            "deadline_type": d.deadline_type,
            "period": d.period,
            "due_date": d.due_date,
            "status": d.status,
            "days_remaining": days_remaining,
            "urgency_level": compute_deadline_urgency(d, today),
            "milestone_label": label,
            "payment_amount": d.payment_amount,
        })
    return result
