"""Timeline computation for tax deadlines."""

from datetime import date

from app.businesses.services.business_lookup import get_business_or_raise


_MILESTONE_LABELS: dict[str, str] = {
    "vat_bimonthly":  'הגשת דוח מע"מ דו-חודשי',
    "vat_monthly":    'הגשת דוח מע"מ חודשי',
    "advance_payment": "תשלום מקדמה",
    "annual_report":   "הגשת דוח שנתי",
    "national_insurance": "תשלום ביטוח לאומי",
}


def build_timeline(business_id: int, business_repo, deadline_repo) -> list[dict]:
    """Return deadlines sorted by due_date asc with days_remaining and milestone_label."""
    get_business_or_raise(business_repo.db, business_id)
    deadlines = deadline_repo.list_by_business(business_id)
    today = date.today()
    result = []
    for d in sorted(deadlines, key=lambda x: x.due_date):
        days_remaining = (d.due_date - today).days
        label = _MILESTONE_LABELS.get(d.deadline_type.value, d.deadline_type.value)
        result.append({
            "id": d.id,
            "business_id": d.business_id,
            "deadline_type": d.deadline_type,
            "period": d.period,
            "due_date": d.due_date,
            "status": d.status,
            "days_remaining": days_remaining,
            "milestone_label": label,
            "payment_amount": float(d.payment_amount) if d.payment_amount is not None else None,
        })
    return result
