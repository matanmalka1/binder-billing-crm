import os
from types import SimpleNamespace
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.businesses.models.business import Business, BusinessType
from app.clients.models.client import Client
from app.reports.services.export_service import ExportService
from app.reports.services.reports_service import AgingReportService


def _client_and_business(db, suffix: str) -> tuple[Client, Business]:
    c = Client(
        full_name=f"Aging Service Client {suffix}",
        id_number=f"AGING-SVC-{suffix}",
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    b = db.query(Business).filter(Business.client_id == c.id).first()
    if b is None:
        b = Business(
            client_id=c.id,
            business_name=c.full_name,
            business_type=BusinessType.COMPANY,
            opened_at=date.today(),
        )
        db.add(b)
        db.commit()
        db.refresh(b)
    return c, b


def _charge(db, business_id: int, amount: str, issued_days_ago: int):
    issued_at = date.today() - timedelta(days=issued_days_ago)
    charge = Charge(
        business_id=business_id,
        amount=Decimal(amount),
        charge_type=ChargeType.CONSULTATION_FEE,
        status=ChargeStatus.ISSUED,
        issued_at=issued_at,
        created_at=issued_at,
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


def test_aging_report_service_calculates_buckets(test_db):
    _, b = _client_and_business(test_db, "1")
    _charge(test_db, b.id, "100.00", 5)
    _charge(test_db, b.id, "200.00", 40)
    _charge(test_db, b.id, "300.00", 70)
    _charge(test_db, b.id, "400.00", 120)

    report = AgingReportService(test_db).generate_aging_report()

    assert report["total_outstanding"] == 1000.0
    assert report["summary"]["total_current"] == 100.0
    assert report["summary"]["total_30_days"] == 200.0
    assert report["summary"]["total_60_days"] == 300.0
    assert report["summary"]["total_90_plus"] == 400.0


def test_export_service_generates_excel_and_pdf_files(test_db):
    _, b = _client_and_business(test_db, "2")
    _charge(test_db, b.id, "150.00", 20)

    report_data = AgingReportService(test_db).generate_aging_report()
    exporter = ExportService()

    excel = exporter.export_aging_report_to_excel(report_data)
    pdf = exporter.export_aging_report_to_pdf(report_data)

    assert excel["format"] == "excel"
    assert pdf["format"] == "pdf"
    assert os.path.exists(excel["filepath"])
    assert os.path.exists(pdf["filepath"])


def test_aging_report_service_skips_rows_without_matching_business(test_db):
    service = AgingReportService(test_db)

    service.charge_repo = SimpleNamespace(
        get_aging_buckets=lambda as_of_date: [
            SimpleNamespace(
                business_id=999_999,
                total=100,
                current=100,
                days_30=0,
                days_60=0,
                days_90_plus=0,
                oldest_issued_at=None,
            )
        ]
    )
    service.business_repo = SimpleNamespace(list_by_ids=lambda ids: [])

    report = service.generate_aging_report(as_of_date=date(2026, 3, 1))

    assert report["items"] == []
    assert report["total_outstanding"] == 0.0
    assert report["summary"]["total_clients"] == 0


def test_export_service_excel_import_error(monkeypatch):
    import builtins
    from app.reports.services import export_excel

    original_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "openpyxl":
            raise ImportError("missing openpyxl")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(ImportError):
        export_excel.export_aging_report_to_excel(
            {"report_date": date.today(), "items": [], "summary": {}, "total_outstanding": 0},
            "/tmp",
        )


def test_export_service_pdf_import_error(monkeypatch):
    import builtins
    from app.reports.services import export_pdf

    original_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name.startswith("reportlab"):
            raise ImportError("missing reportlab")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(ImportError):
        export_pdf.export_aging_report_to_pdf(
            {"report_date": date.today(), "items": [], "summary": {}, "total_outstanding": 0},
            "/tmp",
        )
