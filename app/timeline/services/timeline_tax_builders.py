from app.timeline.labels import ANNUAL_REPORT_STATUS_HE


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
