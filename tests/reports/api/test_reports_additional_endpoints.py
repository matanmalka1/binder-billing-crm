from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportStatus,
    ClientTypeForReport,
    DeadlineType,
)
from app.annual_reports.models.annual_report_model import AnnualReport
from app.businesses.models.business import Business, EntityType
from app.businesses.models.business_tax_profile import VatType
from app.clients.models.client import Client
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem


def _create_client_and_business(test_db, suffix: str) -> tuple[Client, Business]:
    crm_client = Client(
        full_name=f"Reports Client {suffix}",
        id_number=f"RPT-{suffix}",
    )
    test_db.add(crm_client)
    test_db.commit()
    test_db.refresh(crm_client)

    business = test_db.query(Business).filter(Business.client_id == crm_client.id).first()
    if business is None:
        business = Business(
            client_id=crm_client.id,
            business_name=crm_client.full_name,
            entity_type=EntityType.COMPANY_LTD,
            opened_at=date(2025, 1, 1),
        )
        test_db.add(business)
        test_db.commit()
        test_db.refresh(business)
    return crm_client, business


def test_reports_vat_compliance_endpoint(client, test_db, advisor_headers, test_user):
    crm_client, business = _create_client_and_business(test_db, "VAT")
    now = datetime.now(UTC)

    filed = VatWorkItem(
        business_id=business.id,
        created_by=test_user.id,
        period="2026-01",
        period_type=VatType.MONTHLY,
        status=VatWorkItemStatus.FILED,
        filed_at=datetime(2026, 3, 1, 9, 0, 0),
        updated_at=now,
    )
    stale_pending = VatWorkItem(
        business_id=business.id,
        created_by=test_user.id,
        period="2026-02",
        period_type=VatType.MONTHLY,
        status=VatWorkItemStatus.PENDING_MATERIALS,
        updated_at=now - timedelta(days=40),
    )
    test_db.add_all([filed, stale_pending])
    test_db.commit()

    response = client.get("/api/v1/reports/vat-compliance?year=2026", headers=advisor_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["year"] == 2026
    assert payload["total_clients"] == 1
    assert payload["items"][0]["periods_expected"] == 2
    assert payload["items"][0]["periods_filed"] == 1
    assert payload["items"][0]["late_count"] == 1
    assert payload["stale_pending"][0]["period"] == "2026-02"
    assert payload["stale_pending"][0]["days_pending"] >= 40


def test_reports_advance_payments_endpoint_month_filter(client, test_db, advisor_headers):
    _, business = _create_client_and_business(test_db, "ADV")

    jan = AdvancePayment(
        business_id=business.id,
        period="2026-01",
        period_months_count=1,
        expected_amount=Decimal("1000.00"),
        paid_amount=Decimal("500.00"),
        status=AdvancePaymentStatus.OVERDUE,
        due_date=date(2026, 1, 15),
    )
    feb = AdvancePayment(
        business_id=business.id,
        period="2026-02",
        period_months_count=1,
        expected_amount=Decimal("700.00"),
        paid_amount=Decimal("700.00"),
        status=AdvancePaymentStatus.PAID,
        due_date=date(2026, 2, 15),
    )
    test_db.add_all([jan, feb])
    test_db.commit()

    response = client.get(
        "/api/v1/reports/advance-payments?year=2026&month=1",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["year"] == 2026
    assert payload["month"] == 1
    assert payload["total_expected"] == 1000.0
    assert payload["total_paid"] == 500.0
    assert payload["total_gap"] == 500.0
    assert payload["items"][0]["overdue_count"] == 1


def test_reports_annual_reports_endpoint(client, test_db, advisor_headers, test_user):
    crm_client, business = _create_client_and_business(test_db, "ANR")
    report = AnnualReport(
        business_id=business.id,
        created_by=test_user.id,
        tax_year=2026,
        client_type=ClientTypeForReport.CORPORATION,
        form_type=AnnualReportForm.FORM_6111,
        status=AnnualReportStatus.SUBMITTED,
        deadline_type=DeadlineType.STANDARD,
        filing_deadline=datetime(2027, 4, 30, 0, 0, 0),
    )
    test_db.add(report)
    test_db.commit()

    response = client.get("/api/v1/reports/annual-reports?tax_year=2026", headers=advisor_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["tax_year"] == 2026
    assert payload["total"] == 1
    assert payload["statuses"][0]["status"] == "submitted"
    assert payload["statuses"][0]["count"] == 1
    assert payload["statuses"][0]["clients"][0]["client_name"] == crm_client.full_name


def test_reports_aging_export_invalid_format_returns_422(client, advisor_headers):
    response = client.get("/api/v1/reports/aging/export?format=csv", headers=advisor_headers)
    assert response.status_code == 422
