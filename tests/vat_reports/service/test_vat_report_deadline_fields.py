from unittest.mock import MagicMock

from app.common.enums import SubmissionMethod
from app.vat_reports.services import vat_report_queries


def test_compute_deadline_fields_rolls_december_to_next_year():
    item = MagicMock()
    item.period = "2030-12"

    result = vat_report_queries.compute_deadline_fields(item)

    assert str(result["submission_deadline"]) == "2031-01-15"
    assert str(result["statutory_deadline"]) == "2031-01-15"
    assert str(result["extended_deadline"]) == "2031-01-19"
    assert isinstance(result["days_until_deadline"], int)
    assert isinstance(result["is_overdue"], bool)


def test_compute_deadline_fields_manual_filer_uses_statutory():
    item = MagicMock()
    item.period = "2030-06"

    result = vat_report_queries.compute_deadline_fields(
        item, submission_method=SubmissionMethod.MANUAL
    )

    assert str(result["submission_deadline"]) == "2030-07-15"
    assert str(result["statutory_deadline"]) == "2030-07-15"
    assert str(result["extended_deadline"]) == "2030-07-19"


def test_compute_deadline_fields_online_filer_uses_extended():
    item = MagicMock()
    item.period = "2030-06"

    result = vat_report_queries.compute_deadline_fields(
        item, submission_method=SubmissionMethod.ONLINE
    )

    assert str(result["submission_deadline"]) == "2030-07-19"
    assert str(result["statutory_deadline"]) == "2030-07-15"
    assert str(result["extended_deadline"]) == "2030-07-19"


def test_compute_deadline_fields_invalid_period_returns_nones(caplog):
    item = MagicMock()
    item.period = "bad-period"

    with caplog.at_level("WARNING"):
        result = vat_report_queries.compute_deadline_fields(item)

    assert result == {
        "submission_deadline": None,
        "statutory_deadline": None,
        "extended_deadline": None,
        "days_until_deadline": None,
        "is_overdue": None,
    }
    assert "Failed to compute deadline for period 'bad-period'" in caplog.text
