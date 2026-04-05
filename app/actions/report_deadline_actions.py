"""Action contracts for tax deadlines and annual reports."""

from __future__ import annotations

from typing import Any

from app.actions.action_helpers import _generate_action_id, _value, build_action
from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.tax_deadline.models.tax_deadline import TaxDeadline, TaxDeadlineStatus
from app.users.models.user import UserRole

SUBMIT_BLOCKED_STATUSES = {
    AnnualReportStatus.SUBMITTED.value,
    AnnualReportStatus.AMENDED.value,
    AnnualReportStatus.ACCEPTED.value,
    AnnualReportStatus.ASSESSMENT_ISSUED.value,
    AnnualReportStatus.OBJECTION_FILED.value,
    AnnualReportStatus.CLOSED.value,
}


def get_tax_deadline_actions(
    deadline: TaxDeadline,
    *,
    user_role: UserRole | str | None = None,
) -> list[dict[str, Any]]:
    """Return executable actions for a tax deadline."""
    if user_role not in (None, UserRole.ADVISOR, UserRole.ADVISOR.value):
        return []

    status = _value(deadline.status)
    actions: list[dict[str, Any]] = []

    if status != TaxDeadlineStatus.COMPLETED.value:
        actions.append(
            build_action(
                key="complete",
                label="סימון כהושלם",
                method="post",
                endpoint=f"/tax-deadlines/{deadline.id}/complete",
                action_id=_generate_action_id("tax_deadline", deadline.id, "complete"),
            )
        )

    actions.append(
        build_action(
            key="edit",
            label="עריכה",
            method="put",
            endpoint=f"/tax-deadlines/{deadline.id}",
            action_id=_generate_action_id("tax_deadline", deadline.id, "edit"),
        )
    )

    return actions


def get_annual_report_actions(report_id: int, status: str) -> list[dict[str, Any]]:
    """Return executable actions for an annual report based on its status."""
    actions: list[dict[str, Any]] = []

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
