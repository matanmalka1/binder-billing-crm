from datetime import date, datetime
from decimal import Decimal

from app.advance_payments.models.advance_payment import AdvancePayment
from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportStatus,
    ClientTypeForReport,
)
from app.annual_reports.models.annual_report_model import AnnualReport
from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.models import Client, ClientType
from app.permanent_documents.models.permanent_document import DocumentType, PermanentDocument
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem


def _seed_client_with_data(db, user_id: int):
    year = datetime.utcnow().year
    client = Client(
        full_name="Status Card Client",
        id_number="STAT-001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    # VAT periods: one filed, one in progress
    db.add_all(
        [
            VatWorkItem(
                client_id=client.id,
                created_by=user_id,
                period=f"{year}-01",
                status=VatWorkItemStatus.FILED,
                total_output_vat=Decimal("800.00"),
                total_input_vat=Decimal("200.00"),
                net_vat=Decimal("600.00"),
            ),
            VatWorkItem(
                client_id=client.id,
                created_by=user_id,
                period=f"{year}-02",
                status=VatWorkItemStatus.READY_FOR_REVIEW,
                total_output_vat=Decimal("900.00"),
                total_input_vat=Decimal("300.00"),
                net_vat=Decimal("600.00"),
            ),
        ]
    )

    # Annual report for current year
    db.add(
        AnnualReport(
            client_id=client.id,
            created_by=user_id,
            tax_year=year,
            client_type=ClientTypeForReport.CORPORATION,
            form_type=AnnualReportForm.FORM_6111,
            status=AnnualReportStatus.IN_PREPARATION,
            filing_deadline=datetime(year, 12, 31),
            refund_due=Decimal("50.00"),
            tax_due=Decimal("75.00"),
        )
    )

    # Charges: only ISSUED should count
    db.add_all(
        [
            Charge(
                client_id=client.id,
                amount=Decimal("120.00"),
                charge_type=ChargeType.RETAINER,
                status=ChargeStatus.ISSUED,
                created_by=user_id,
            ),
            Charge(
                client_id=client.id,
                amount=Decimal("999.00"),
                charge_type=ChargeType.ONE_TIME,
                status=ChargeStatus.PAID,
                created_by=user_id,
            ),
        ]
    )

    # Advance payments
    db.add_all(
        [
            AdvancePayment(
                client_id=client.id,
                month=1,
                year=year,
                paid_amount=Decimal("200.00"),
                due_date=date(year, 2, 15),
            ),
            AdvancePayment(
                client_id=client.id,
                month=2,
                year=year,
                paid_amount=Decimal("150.00"),
                due_date=date(year, 3, 15),
            ),
        ]
    )

    # Binders: active + returned (returned should be excluded from counts)
    db.add_all(
        [
            Binder(
                client_id=client.id,
                binder_number="STAT-BND-1",
                binder_type=BinderType.OTHER,
                received_at=date.today(),
                received_by=user_id,
                status=BinderStatus.IN_OFFICE,
            ),
            Binder(
                client_id=client.id,
                binder_number="STAT-BND-2",
                binder_type=BinderType.OTHER,
                received_at=date.today(),
                received_by=user_id,
                status=BinderStatus.RETURNED,
            ),
        ]
    )

    # Permanent documents
    db.add_all(
        [
            PermanentDocument(
                client_id=client.id,
                document_type=DocumentType.ID_COPY,
                storage_key="clients/stat/id.pdf",
                uploaded_by=user_id,
                is_present=True,
            ),
            PermanentDocument(
                client_id=client.id,
                document_type=DocumentType.POWER_OF_ATTORNEY,
                storage_key="clients/stat/poa.pdf",
                uploaded_by=user_id,
                is_present=False,
            ),
        ]
    )

    db.commit()
    return client, year


def test_client_status_card_aggregates_modules(client, test_db, advisor_headers, test_user):
    crm_client, year = _seed_client_with_data(test_db, test_user.id)

    resp = client.get(f"/api/v1/clients/{crm_client.id}/status-card", headers=advisor_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["client_id"] == crm_client.id
    assert data["year"] == year

    vat = data["vat"]
    assert vat["periods_total"] == 2
    assert vat["periods_filed"] == 1
    assert vat["latest_period"] == f"{year}-02"
    assert Decimal(str(vat["net_vat_total"])) == Decimal("1200.00")

    annual = data["annual_report"]
    assert annual["status"] == "in_preparation"
    assert annual["form_type"] == "6111"
    assert Decimal(str(annual["refund_due"])) == Decimal("50.00")
    assert Decimal(str(annual["tax_due"])) == Decimal("75.00")

    charges = data["charges"]
    assert Decimal(str(charges["total_outstanding"])) == Decimal("120.00")
    assert charges["unpaid_count"] == 1

    advances = data["advance_payments"]
    assert Decimal(str(advances["total_paid"])) == Decimal("350.00")
    assert advances["count"] == 2

    binders = data["binders"]
    assert binders["active_count"] == 1
    assert binders["in_office_count"] == 1

    docs = data["documents"]
    assert docs["total_count"] == 2
    assert docs["present_count"] == 1
