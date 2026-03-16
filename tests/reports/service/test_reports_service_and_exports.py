import os
from datetime import date, timedelta
from decimal import Decimal

from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.models import Client, ClientType
from app.reports.services.export_service import ExportService
from app.reports.services.reports_service import AgingReportService


def _client(db, suffix: str) -> Client:
    c = Client(
        full_name=f"Aging Service Client {suffix}",
        id_number=f"AGING-SVC-{suffix}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _charge(db, client_id: int, amount: str, issued_days_ago: int):
    issued_at = date.today() - timedelta(days=issued_days_ago)
    charge = Charge(
        client_id=client_id,
        amount=Decimal(amount),
        currency="ILS",
        charge_type=ChargeType.ONE_TIME,
        status=ChargeStatus.ISSUED,
        issued_at=issued_at,
        created_at=issued_at,
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


def test_aging_report_service_calculates_buckets(test_db):
    c = _client(test_db, "1")
    _charge(test_db, c.id, "100.00", 5)
    _charge(test_db, c.id, "200.00", 40)
    _charge(test_db, c.id, "300.00", 70)
    _charge(test_db, c.id, "400.00", 120)

    report = AgingReportService(test_db).generate_aging_report()

    assert report["total_outstanding"] == 1000.0
    assert report["summary"]["total_current"] == 100.0
    assert report["summary"]["total_30_days"] == 200.0
    assert report["summary"]["total_60_days"] == 300.0
    assert report["summary"]["total_90_plus"] == 400.0


def test_export_service_generates_excel_and_pdf_files(test_db):
    c = _client(test_db, "2")
    _charge(test_db, c.id, "150.00", 20)

    report_data = AgingReportService(test_db).generate_aging_report()
    exporter = ExportService(test_db)

    excel = exporter.export_aging_report_to_excel(report_data)
    pdf = exporter.export_aging_report_to_pdf(report_data)

    assert excel["format"] == "excel"
    assert pdf["format"] == "pdf"
    assert os.path.exists(excel["filepath"])
    assert os.path.exists(pdf["filepath"])
