from datetime import datetime

from app.timeline.labels import ANNUAL_REPORT_STATUS_HE, DEADLINE_TYPE_HE


def tax_deadline_due_event(deadline) -> dict:
    type_he = DEADLINE_TYPE_HE.get(deadline.deadline_type.value, deadline.deadline_type.value)
    due_str = deadline.due_date.strftime("%d/%m/%Y")
    amount_part = (
        f" — ₪{float(deadline.payment_amount):,.2f}" if deadline.payment_amount else ""
    )
    return {
        "event_type": "tax_deadline_due",
        "timestamp": datetime.combine(deadline.due_date, datetime.min.time()),
        "binder_id": None,
        "charge_id": None,
        "description": f"מועד {type_he}: {due_str}{amount_part}",
        "metadata": {"tax_deadline_id": deadline.id},
        "available_actions": [],
    }


def annual_report_status_changed_event(report) -> dict:
    form_str = report.form_type.value if report.form_type else ""
    status_he = ANNUAL_REPORT_STATUS_HE.get(report.status.value, report.status.value)
    return {
        "event_type": "annual_report_status_changed",
        "timestamp": report.updated_at,
        "binder_id": None,
        "charge_id": None,
        "description": f"דוח שנתי {form_str} ({report.tax_year}): {status_he}",
        "metadata": {"annual_report_id": report.id},
        "available_actions": [],
    }
