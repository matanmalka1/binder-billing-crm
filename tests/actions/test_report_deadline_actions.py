from types import SimpleNamespace

from app.actions.report_deadline_actions import (
    get_annual_report_actions,
    get_tax_deadline_actions,
)
from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.tax_deadline.models.tax_deadline import TaxDeadlineStatus
from app.users.models.user import UserRole


def test_get_tax_deadline_actions_non_completed_has_complete_and_edit():
    deadline = SimpleNamespace(id=3, status=TaxDeadlineStatus.PENDING)

    actions = get_tax_deadline_actions(deadline)

    assert [action["key"] for action in actions] == ["complete", "edit", "delete"]
    assert actions[0]["id"] == "tax_deadline-3-complete"
    assert actions[1]["id"] == "tax_deadline-3-edit"
    assert actions[2]["id"] == "tax_deadline-3-delete"
    assert actions[2]["confirm"]["confirm_label"] == "מחיקה"

def test_get_tax_deadline_actions_completed_has_only_reopen():
    deadline = SimpleNamespace(id=4, status=TaxDeadlineStatus.COMPLETED)

    actions = get_tax_deadline_actions(deadline)

    assert [action["key"] for action in actions] == ["reopen"]
    assert actions[0]["endpoint"] == "/tax-deadlines/4/reopen"


def test_get_tax_deadline_actions_canceled_has_no_actions():
    deadline = SimpleNamespace(id=6, status=TaxDeadlineStatus.CANCELED)

    actions = get_tax_deadline_actions(deadline)

    assert actions == []


def test_get_tax_deadline_actions_secretary_has_no_actions():
    deadline = SimpleNamespace(id=5, status=TaxDeadlineStatus.PENDING)

    actions = get_tax_deadline_actions(deadline, user_role=UserRole.SECRETARY)

    assert actions == []


def test_get_annual_report_actions_submitted_has_amend_only():
    actions = get_annual_report_actions(
        report_id=8,
        status=AnnualReportStatus.SUBMITTED.value,
    )

    assert [action["key"] for action in actions] == ["amend"]
    assert actions[0]["id"] == "annual_report-8-amend"


def test_get_annual_report_actions_open_status_has_submit():
    actions = get_annual_report_actions(
        report_id=9,
        status=AnnualReportStatus.IN_PREPARATION.value,
    )

    assert [action["key"] for action in actions] == ["submit"]
    assert actions[0]["id"] == "annual_report-9-submit"


def test_get_annual_report_actions_closed_states_have_no_actions():
    statuses = [
        AnnualReportStatus.AMENDED.value,
        AnnualReportStatus.ACCEPTED.value,
        AnnualReportStatus.ASSESSMENT_ISSUED.value,
        AnnualReportStatus.OBJECTION_FILED.value,
        AnnualReportStatus.CLOSED.value,
    ]

    for state in statuses:
        assert get_annual_report_actions(report_id=10, status=state) == []
