"""Unit tests for vat_reports/api/serializers.py routing."""

from datetime import date
from unittest.mock import MagicMock, patch

from app.common.enums import SubmissionMethod
from app.vat_reports.api.serializers import serialize_enriched_work_item


def test_serializer_calls_get_vat_deadline_fields_not_raw_compute():
    """serialize_enriched_work_item must delegate to get_vat_deadline_fields.

    Snapshot vs. legacy routing is owned by get_vat_deadline_fields, not the serializer.
    """
    item = MagicMock()
    item.due_date_effective = date(2026, 9, 24)
    item.submission_method = SubmissionMethod.ONLINE
    item.assigned_to = None
    item.filed_by = None
    item.client_record_id = 1

    snap_result = {
        "submission_deadline": date(2026, 9, 28),
        "statutory_deadline": date(2026, 9, 24),
        "extended_deadline": date(2026, 9, 28),
        "days_until_deadline": 5,
        "is_overdue": False,
    }

    with (
        patch(
            "app.vat_reports.api.serializers.get_vat_deadline_fields",
            return_value=snap_result,
        ) as mock_deadline,
        patch("app.vat_reports.api.serializers.VatWorkItemResponse") as MockResp,
        patch(
            "app.vat_reports.api.serializers.get_vat_work_item_actions", return_value=[]
        ),
    ):
        MockResp.model_validate.return_value = MagicMock()
        result = serialize_enriched_work_item(
            item,
            office_client_number_map={},
            name_map={},
            id_number_map={},
            status_map={},
            user_map={},
        )

    mock_deadline.assert_called_once_with(item, SubmissionMethod.ONLINE)
    assert result.submission_deadline == date(2026, 9, 28)
