from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.businesses.models.business import Business
from app.businesses.models.business_tax_profile import VatType
from app.clients.models.client import Client
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.vat_reports.services.vat_export_pdf import export_vat_to_pdf
from app.vat_reports.services.vat_export_service import export_to_pdf
from app.vat_reports.services.vat_report_service import VatReportService


def _user(test_db) -> User:
    user = User(
        full_name="VAT Export User",
        email="vat.export.user@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _business(test_db) -> Business:
    client = Client(full_name="VAT Export Client", id_number="VEP001")
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return test_db.get(Business, client.id)


def test_export_to_pdf_filters_periods_by_year_and_delegates(test_db, monkeypatch):
    user = _user(test_db)
    business = _business(test_db)
    service = VatReportService(test_db)
    item_2026 = service.work_item_repo.create(
        business_id=business.id, period="2026-01", period_type=VatType.MONTHLY, created_by=user.id
    )
    item_2025 = service.work_item_repo.create(
        business_id=business.id, period="2025-12", period_type=VatType.MONTHLY, created_by=user.id
    )
    service.work_item_repo.update_vat_totals(item_2026.id, 170.0, 20.0, 1000.0, 200.0)
    service.work_item_repo.update_vat_totals(item_2025.id, 85.0, 10.0, 500.0, 100.0)

    captured = {}

    def _fake_export(business_name, business_id, year, periods, export_dir):
        captured["business_name"] = business_name
        captured["business_id"] = business_id
        captured["year"] = year
        captured["periods"] = periods
        captured["export_dir"] = export_dir
        return {
            "format": "pdf",
            "filepath": "/tmp/fake.pdf",
            "filename": "fake.pdf",
            "generated_at": datetime.now(UTC),
        }

    monkeypatch.setattr(
        "app.vat_reports.services.vat_export_service.export_vat_to_pdf",
        _fake_export,
    )

    payload = export_to_pdf(test_db, business.id, 2026)
    assert payload["format"] == "pdf"
    assert captured["business_id"] == business.id
    assert captured["year"] == 2026
    assert len(captured["periods"]) == 1
    assert captured["periods"][0].period == "2026-01"


def test_export_vat_to_pdf_generates_file_when_reportlab_available_or_raises():
    try:
        import reportlab  # noqa: F401
    except ImportError:
        with pytest.raises(ImportError):
            export_vat_to_pdf(
                client_name="Client",
                business_id=1,
                year=2026,
                periods=[],
                export_dir="/tmp",
            )
        return

    from app.vat_reports.models.vat_enums import VatWorkItemStatus
    from app.vat_reports.schemas.vat_client_summary_schema import VatPeriodRow

    period = VatPeriodRow(
        period="2026-01",
        status=VatWorkItemStatus.FILED,
        total_output_vat=Decimal("170.00"),
        total_input_vat=Decimal("20.00"),
        net_vat=Decimal("150.00"),
        final_vat_amount=Decimal("150.00"),
        filed_at=datetime.now(UTC) - timedelta(days=1),
    )

    payload = export_vat_to_pdf(
        client_name="Client",
        business_id=1,
        year=2026,
        periods=[period],
        export_dir="/tmp",
    )
    assert payload["format"] == "pdf"
    assert Path(payload["filepath"]).exists()
