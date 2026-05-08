"""Action contracts for annual reports."""

from __future__ import annotations

from app.actions.action_helpers import (
    ActionContract,
    _generate_action_id,
    build_action,
)
from app.annual_reports.models.annual_report_enums import AnnualReportStatus

SUBMIT_BLOCKED_STATUSES = {
    AnnualReportStatus.SUBMITTED.value,
    AnnualReportStatus.AMENDED.value,
    AnnualReportStatus.ACCEPTED.value,
    AnnualReportStatus.ASSESSMENT_ISSUED.value,
    AnnualReportStatus.OBJECTION_FILED.value,
    AnnualReportStatus.CLOSED.value,
}


def get_annual_report_actions(report_id: int, status: str) -> list[ActionContract]:
    """Return executable actions for an annual report based on its status."""
    actions: list[ActionContract] = []

    if status == AnnualReportStatus.SUBMITTED.value:
        actions.append(
            build_action(
                key="amend",
                label="תיקון דוח",
                method="post",
                endpoint=f"/annual-reports/{report_id}/amend",
                action_id=_generate_action_id("annual_report", report_id, "amend"),
            )
        )

    if status not in SUBMIT_BLOCKED_STATUSES:
        actions.append(
            build_action(
                key="submit",
                label="הגשה לרשות המסים",
                method="post",
                endpoint=f"/annual-reports/{report_id}/submit",
                action_id=_generate_action_id("annual_report", report_id, "submit"),
            )
        )

    return actions
