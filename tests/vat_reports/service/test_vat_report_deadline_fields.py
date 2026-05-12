from datetime import date
from unittest.mock import MagicMock

import pytest

from app.common.enums import SubmissionMethod
from app.vat_reports.services.vat_report_queries import get_vat_deadline_fields


def test_get_vat_deadline_fields_uses_effective_snapshot_for_all_methods():
    item = MagicMock()
    item.due_date_original = date(2026, 9, 24)
    item.due_date_effective = date(2026, 10, 1)

    for method in (None, SubmissionMethod.MANUAL, SubmissionMethod.ONLINE):
        result = get_vat_deadline_fields(item, method)
        assert result["submission_deadline"] == date(2026, 10, 1)
        assert result["statutory_deadline"] == date(2026, 9, 24)
        assert result["extended_deadline"] == date(2026, 10, 1)
        assert isinstance(result["days_until_deadline"], int)
        assert isinstance(result["is_overdue"], bool)


def test_get_vat_deadline_fields_rejects_missing_effective_snapshot():
    item = MagicMock()
    item.id = 10
    item.due_date_effective = None

    with pytest.raises(ValueError, match="missing due_date_effective"):
        get_vat_deadline_fields(item, SubmissionMethod.MANUAL)
