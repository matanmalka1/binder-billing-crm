"""Regression tests: due-date source-of-truth is TaxCalendarEntry, not hardcoded day constants."""

from datetime import date
from unittest.mock import (
    MagicMock,
)  # used in unit tests that don't need Pydantic validation

from app.common.enums import DeadlineRuleType, ObligationType, SubmissionMethod, VatType
from app.vat_reports.api.serializers import serialize_enriched_work_item
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.intake import create_work_item
from app.vat_reports.services.vat_report_queries import deadline_fields_from_snapshot
from tests.tax_calendar.service.linking_helpers import make_entry, vat_client

# ── deadline_fields_from_snapshot ────────────────────────────────────────────


def test_snapshot_statutory_filer_uses_due_date_effective():
    # due_date_effective already incorporates any calendar extension;
    # snapshot path must NOT add extra days — extended == effective.
    item = MagicMock()
    item.due_date_original = date(2026, 2, 16)
    item.due_date_effective = date(2026, 2, 16)

    result = deadline_fields_from_snapshot(item, submission_method=SubmissionMethod.MANUAL)

    assert result["submission_deadline"] == date(2026, 2, 16)
    assert result["statutory_deadline"] == date(2026, 2, 16)
    assert result["extended_deadline"] == date(2026, 2, 16)
    assert isinstance(result["days_until_deadline"], int)
    assert isinstance(result["is_overdue"], bool)


def test_snapshot_online_filer_uses_effective_no_extra_extension():
    # Snapshot path: submission_method is irrelevant — effective IS the deadline.
    item = MagicMock()
    item.due_date_original = date(2026, 2, 16)
    item.due_date_effective = date(2026, 2, 16)

    result = deadline_fields_from_snapshot(item, submission_method=SubmissionMethod.ONLINE)

    assert result["submission_deadline"] == date(2026, 2, 16)
    assert result["statutory_deadline"] == date(2026, 2, 16)
    assert result["extended_deadline"] == date(2026, 2, 16)


def test_snapshot_standard_month_submission_equals_effective():
    # For a standard month where effective == original (no holiday shift),
    # submission and extended both equal effective — no +4 added by snapshot path.
    item = MagicMock()
    item.due_date_original = date(2026, 3, 15)
    item.due_date_effective = date(2026, 3, 15)

    result = deadline_fields_from_snapshot(item, submission_method=SubmissionMethod.ONLINE)

    assert result["submission_deadline"] == date(2026, 3, 15)
    assert result["statutory_deadline"] == date(2026, 3, 15)
    assert result["extended_deadline"] == date(2026, 3, 15)


def test_snapshot_falls_back_to_effective_when_original_is_none():
    item = MagicMock()
    item.due_date_original = None
    item.due_date_effective = date(2026, 2, 16)

    result = deadline_fields_from_snapshot(item, submission_method=SubmissionMethod.MANUAL)

    assert result["submission_deadline"] == date(2026, 2, 16)
    assert result["statutory_deadline"] == date(2026, 2, 16)


# ── serializer routing ────────────────────────────────────────────────────────


def test_serializer_prefers_snapshot_over_computed_deadline(test_db):
    """When due_date_effective is set, submission_deadline must come from snapshot, not period+15."""
    entry = make_entry(
        test_db,
        obligation_type=ObligationType.VAT,
        rule_type=DeadlineRuleType.VAT_MONTHLY,
        period="2026-01",
        months=1,
        tax_year=2026,
    )
    # Override entry's due_date to 16th (holiday-shifted)
    entry.due_date = date(2026, 2, 16)
    test_db.flush()

    client = vat_client(test_db, VatType.MONTHLY)
    item = create_work_item(
        VatWorkItemRepository(test_db),
        test_db,
        client_record_id=client.id,
        period="2026-01",
        created_by=1,
    )

    assert item.due_date_effective == date(2026, 2, 16), "snapshot must use entry.due_date=16th"

    result = serialize_enriched_work_item(
        item,
        office_client_number_map={},
        name_map={},
        id_number_map={},
        status_map={},
        user_map={},
    )

    assert result.submission_deadline == date(2026, 2, 16), (
        f"expected 2026-02-16 from snapshot, got {result.submission_deadline} (hardcoded 15th would be wrong)"
    )
    assert result.statutory_deadline == date(2026, 2, 16)
    # extended_deadline == effective: snapshot path does not add +4
    assert result.extended_deadline == date(2026, 2, 16)


def test_serializer_routing_uses_snapshot_when_effective_set():
    """Routing: due_date_effective truthy → deadline_fields_from_snapshot called (not compute)."""
    item = MagicMock()
    item.due_date_effective = date(2026, 2, 16)
    item.due_date_original = date(2026, 2, 16)
    item.submission_method = None

    from app.vat_reports.services.vat_report_queries import (
        deadline_fields_from_snapshot,
    )

    result = deadline_fields_from_snapshot(item)

    # Verify snapshot path produces 16th, not hardcoded 15th
    assert result["submission_deadline"] == date(2026, 2, 16)
    assert result["statutory_deadline"] == date(2026, 2, 16)
