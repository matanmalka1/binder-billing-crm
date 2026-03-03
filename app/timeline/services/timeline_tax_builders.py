from datetime import datetime

DEADLINE_TYPE_HE = {
    "vat": "מע״מ",
    "advance_payment": "מקדמה",
    "national_insurance": "ביטוח לאומי",
    "annual_report": "דוח שנתי",
    "other": "אחר",
}

ANNUAL_REPORT_STATUS_HE = {
    "not_started": "טרם התחיל",
    "collecting_docs": "איסוף מסמכים",
    "docs_complete": "מסמכים התקבלו",
    "in_preparation": "בהכנה",
    "pending_client": "ממתין לאישור לקוח",
    "submitted": "הוגש",
    "accepted": "התקבל",
    "assessment_issued": "שומה הוצאה",
    "objection_filed": "השגה הוגשה",
    "closed": "סגור",
}


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
        "actions": [],
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
        "actions": [],
        "available_actions": [],
    }
