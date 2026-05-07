from datetime import date

import pytest

from app.advance_payments.services.advance_payment_generator import generate_annual_schedule
from app.annual_reports.services.annual_report_service import AnnualReportService
from app.common.enums import DeadlineRuleType, ObligationType, VatType
from app.core.exceptions import AppError
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.intake import create_work_item
from tests.tax_calendar.service.linking_helpers import (
    advance_client,
    annual_client,
    make_entry,
    vat_client,
)


def test_advance_payment_generation_links_matching_tax_calendar_entry(test_db):
    entry = make_entry(
        test_db,
        obligation_type=ObligationType.ADVANCE_PAYMENT,
        rule_type=DeadlineRuleType.ADVANCE_MONTHLY,
        period="2026-01",
        months=1,
        tax_year=2026,
    )
    client = advance_client(test_db)

    created, skipped = generate_annual_schedule(
        client.id, 2026, test_db, reference_date=date(2025, 12, 31)
    )

    jan = next(payment for payment in created if payment.period == "2026-01")
    assert skipped == 0
    assert jan.tax_calendar_entry_id == entry.id
    assert jan.due_date == date(2026, 2, 15)
    assert jan.status.value == "pending"


def test_advance_payment_generation_leaves_null_without_matching_entry(test_db):
    client = advance_client(test_db)

    created, _ = generate_annual_schedule(
        client.id, 2026, test_db, reference_date=date(2025, 12, 31)
    )

    assert all(payment.tax_calendar_entry_id is None for payment in created)


def test_vat_work_item_monthly_links_matching_tax_calendar_entry(test_db):
    entry = make_entry(
        test_db,
        obligation_type=ObligationType.VAT,
        rule_type=DeadlineRuleType.VAT_MONTHLY,
        period="2026-01",
        months=1,
        tax_year=2026,
    )
    client = vat_client(test_db, VatType.MONTHLY)

    item = create_work_item(
        VatWorkItemRepository(test_db), test_db,
        client_record_id=client.id, period="2026-01", created_by=1,
    )

    assert item.tax_calendar_entry_id == entry.id
    assert item.due_date_original == entry.due_date
    assert item.due_date_effective == entry.due_date
    assert item.status == VatWorkItemStatus.MATERIAL_RECEIVED


def test_vat_work_item_bimonthly_links_matching_tax_calendar_entry(test_db):
    entry = make_entry(
        test_db,
        obligation_type=ObligationType.VAT,
        rule_type=DeadlineRuleType.VAT_BIMONTHLY,
        period="2026-01",
        months=2,
        tax_year=2026,
    )
    client = vat_client(test_db, VatType.BIMONTHLY)

    item = create_work_item(
        VatWorkItemRepository(test_db), test_db,
        client_record_id=client.id, period="2026-01", created_by=1,
    )

    assert item.tax_calendar_entry_id == entry.id
    assert item.due_date_original == entry.due_date
    assert item.due_date_effective == entry.due_date
    assert item.status == VatWorkItemStatus.MATERIAL_RECEIVED


def test_vat_work_item_leaves_snapshots_null_without_matching_entry(test_db):
    client = vat_client(test_db, VatType.MONTHLY)

    item = create_work_item(
        VatWorkItemRepository(test_db), test_db,
        client_record_id=client.id, period="2026-01", created_by=1,
    )

    assert item.tax_calendar_entry_id is None
    assert item.due_date_original is None
    assert item.due_date_effective is None
    assert item.status == VatWorkItemStatus.MATERIAL_RECEIVED


def test_vat_work_item_due_date_original_is_immutable_after_set(test_db):
    entry = make_entry(
        test_db,
        obligation_type=ObligationType.VAT,
        rule_type=DeadlineRuleType.VAT_MONTHLY,
        period="2026-01",
        months=1,
        tax_year=2026,
    )
    client = vat_client(test_db, VatType.MONTHLY)
    item = create_work_item(
        VatWorkItemRepository(test_db), test_db,
        client_record_id=client.id, period="2026-01", created_by=1,
    )

    item.due_date_original = date(2026, 2, 20)

    with pytest.raises(ValueError):
        test_db.flush()
    assert item.due_date_effective == entry.due_date


def test_vat_work_item_effective_due_date_requires_reason_when_changed(test_db):
    client = vat_client(test_db, VatType.MONTHLY)
    item = create_work_item(
        VatWorkItemRepository(test_db), test_db,
        client_record_id=client.id, period="2026-01", created_by=1,
    )
    item.due_date_original = date(2026, 2, 15)
    item.due_date_effective = date(2026, 2, 20)

    with pytest.raises(ValueError):
        test_db.flush()


def test_vat_work_item_effective_due_date_can_change_with_reason(test_db):
    client = vat_client(test_db, VatType.MONTHLY)
    item = create_work_item(
        VatWorkItemRepository(test_db), test_db,
        client_record_id=client.id, period="2026-01", created_by=1,
    )
    item.due_date_original = date(2026, 2, 15)
    item.due_date_effective = date(2026, 2, 20)
    item.due_date_override_reason = "דחייה רשמית"

    test_db.flush()

    assert item.due_date_effective == date(2026, 2, 20)


def test_vat_work_item_effective_due_date_equal_original_needs_no_reason(test_db):
    client = vat_client(test_db, VatType.MONTHLY)
    item = create_work_item(
        VatWorkItemRepository(test_db), test_db,
        client_record_id=client.id, period="2026-01", created_by=1,
    )
    item.due_date_original = date(2026, 2, 15)
    item.due_date_effective = date(2026, 2, 15)

    test_db.flush()

    assert item.due_date_override_reason is None


def test_vat_exempt_keeps_existing_rejection_before_calendar_linking(test_db):
    client = vat_client(test_db, VatType.EXEMPT)

    with pytest.raises(AppError) as exc:
        create_work_item(
            VatWorkItemRepository(test_db), test_db,
            client_record_id=client.id, period="2026-01", created_by=1,
        )

    assert exc.value.code == "VAT.CLIENT_EXEMPT"
    assert test_db.query(VatWorkItem).count() == 0


def test_annual_report_creation_links_matching_tax_calendar_entry(test_db):
    entry = make_entry(
        test_db,
        obligation_type=ObligationType.ANNUAL_REPORT,
        rule_type=DeadlineRuleType.ANNUAL_REPORT,
        period=None,
        months=None,
        tax_year=2026,
    )
    client = annual_client(test_db)

    report = AnnualReportService(test_db).create_report(
        client.id, 2026, "corporation", 1, "Advisor"
    )

    assert report.tax_calendar_entry_id == entry.id
    assert report.status.value == "not_started"
    assert report.filing_deadline.date() == date(2027, 7, 31)
