from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.annual_reports.models.annual_report_enums import AnnualReportForm, AnnualReportStatus
from app.binders.models.binder import BinderStatus
from app.businesses.services.status_card_service import StatusCardService
from app.core.exceptions import NotFoundError
from app.vat_reports.models.vat_work_item import VatWorkItemStatus


def test_get_status_card_raises_when_business_missing(test_db):
    service = StatusCardService(test_db)
    service._business_repo.get_by_id = lambda _business_id: None

    with pytest.raises(NotFoundError) as exc:
        service.get_status_card(123)

    assert exc.value.code == "BUSINESS.NOT_FOUND"


def test_get_status_card_default_year_and_aggregations(test_db):
    service = StatusCardService(test_db)

    business = SimpleNamespace(client_id=88)
    service._business_repo.get_by_id = lambda _business_id: business

    service._vat_repo.list_by_client = lambda _client_id: [
        SimpleNamespace(period="2026-01", net_vat=Decimal("10.00"), status=VatWorkItemStatus.FILED),
        SimpleNamespace(period="2026-02", net_vat=Decimal("5.00"), status=VatWorkItemStatus.MATERIAL_RECEIVED),
        SimpleNamespace(period="2025-12", net_vat=Decimal("99.00"), status=VatWorkItemStatus.FILED),
    ]
    service._annual_repo.get_by_business_year = lambda _business_id, _year: SimpleNamespace(
        status=AnnualReportStatus.SUBMITTED,
        form_type=AnnualReportForm.FORM_1301,
        filing_deadline=datetime(2026, 4, 30),
        refund_due=Decimal("3.50"),
        tax_due=Decimal("1.25"),
    )
    service._charge_repo.list_charges = lambda **_kwargs: [
        SimpleNamespace(amount=Decimal("7.00")),
        SimpleNamespace(amount=Decimal("8.00")),
    ]
    service._advance_repo.list_by_business_year = lambda **_kwargs: (
        [SimpleNamespace(paid_amount=Decimal("2.00")), SimpleNamespace(paid_amount=Decimal("3.00"))],
        2,
    )
    service._binder_repo.list_by_client = lambda _client_id: [
        SimpleNamespace(status=BinderStatus.IN_OFFICE),
        SimpleNamespace(status=BinderStatus.READY_FOR_PICKUP),
        SimpleNamespace(status=BinderStatus.RETURNED),
    ]
    service._doc_repo.list_by_business = lambda _business_id: [
        SimpleNamespace(is_present=True),
        SimpleNamespace(is_present=False),
    ]

    card = service.get_status_card(55, year=2026)

    assert card.client_id == 88
    assert card.year == 2026

    assert card.client_vat.net_vat_total == Decimal("15.00")
    assert card.client_vat.periods_filed == 1
    assert card.client_vat.periods_total == 2
    assert card.client_vat.latest_period == "2026-02"

    assert card.annual_report.status == "submitted"
    assert card.annual_report.form_type == "1301"
    assert card.annual_report.filing_deadline == "2026-04-30"

    assert card.charges.total_outstanding == Decimal("15.00")
    assert card.charges.unpaid_count == 2

    assert card.advance_payments.total_paid == Decimal("5.00")
    assert card.advance_payments.count == 2

    assert card.binders.active_count == 2
    assert card.binders.in_office_count == 1

    assert card.documents.total_count == 2
    assert card.documents.present_count == 1


def test_annual_report_card_empty_when_report_missing(test_db):
    service = StatusCardService(test_db)
    service._annual_repo.get_by_business_year = lambda _business_id, _year: None

    result = service._annual_report_card(1, 2026)

    assert result.status is None
    assert result.form_type is None
    assert result.filing_deadline is None
