from datetime import date
from decimal import Decimal

from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportStatus,
    ClientTypeForReport,
)
from app.annual_reports.models.annual_report_model import AnnualReport
from app.businesses.models.business import Business
from app.common.enums import EntityType
from app.clients.models.client import Client


def _seed_businesses_and_reports(db, creator_id: int, tax_year: int):
    """Create businesses and reports across submission stages for dashboard widget."""
    clients = [
        Client(full_name="Submitted Corp", id_number="DASH-001"),
        Client(full_name="In Prep", id_number="DASH-002"),
        Client(full_name="Collecting Docs", id_number="DASH-003"),
        Client(full_name="Not Started", id_number="DASH-004"),
    ]
    db.add_all(clients)
    db.commit()
    for client in clients:
        db.refresh(client)

    businesses = [
        Business(
            client_id=clients[0].id,
            business_name="Submitted Corp Biz",
            opened_at=date.today(),
        ),
        Business(
            client_id=clients[1].id,
            business_name="In Prep Biz",
            opened_at=date.today(),
        ),
        Business(
            client_id=clients[2].id,
            business_name="Collecting Docs Biz",
            opened_at=date.today(),
        ),
        Business(
            client_id=clients[3].id,
            business_name="Not Started Biz",
            opened_at=date.today(),
        ),
    ]
    db.add_all(businesses)
    db.commit()
    for business in businesses:
        db.refresh(business)

    reports = [
        AnnualReport(
            business_id=businesses[0].id,
            created_by=creator_id,
            tax_year=tax_year,
            client_type=ClientTypeForReport.CORPORATION,
            form_type=AnnualReportForm.FORM_6111,
            status=AnnualReportStatus.SUBMITTED,
            refund_due=Decimal("100.00"),
            tax_due=Decimal("50.00"),
        ),
        AnnualReport(
            business_id=businesses[1].id,
            created_by=creator_id,
            tax_year=tax_year,
            client_type=ClientTypeForReport.INDIVIDUAL,
            form_type=AnnualReportForm.FORM_1301,
            status=AnnualReportStatus.IN_PREPARATION,
            refund_due=Decimal("20.00"),
            tax_due=Decimal("75.00"),
        ),
        AnnualReport(
            business_id=businesses[2].id,
            created_by=creator_id,
            tax_year=tax_year,
            client_type=ClientTypeForReport.SELF_EMPLOYED,
            form_type=AnnualReportForm.FORM_1215,
            status=AnnualReportStatus.COLLECTING_DOCS,
            refund_due=Decimal("0.00"),
            tax_due=Decimal("0.00"),
        ),
        AnnualReport(
            business_id=businesses[3].id,
            created_by=creator_id,
            tax_year=tax_year,
            client_type=ClientTypeForReport.INDIVIDUAL,
            form_type=AnnualReportForm.FORM_1301,
            status=AnnualReportStatus.NOT_STARTED,
        ),
    ]
    db.add_all(reports)
    db.commit()


def test_tax_submission_widget_counts(client, test_db, advisor_headers, test_user):
    tax_year = 2099
    _seed_businesses_and_reports(test_db, creator_id=test_user.id, tax_year=tax_year)

    resp = client.get(
        f"/api/v1/dashboard/tax-submissions?tax_year={tax_year}",
        headers=advisor_headers,
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["tax_year"] == tax_year
    assert data["total_clients"] >= 4
    assert data["reports_submitted"] == 1
    assert data["reports_in_progress"] == 1  # IN_PREPARATION
    # total − submitted − in_progress − material_collection
    assert data["reports_not_started"] == data["total_clients"] - 3
    assert data["submission_percentage"] == round((1 / data["total_clients"]) * 100, 1)

    assert Decimal(str(data["total_refund_due"])) == Decimal("120.00")
    assert Decimal(str(data["total_tax_due"])) == Decimal("125.00")
