from datetime import date
from decimal import Decimal

from tax_rules import get_financial

from app.advance_payments.models.advance_payment import AdvancePayment
from app.annual_reports.models.annual_report_model import AnnualReport
from app.binders.models.binder import Binder
from app.clients.services.client_creation_service import ClientCreationService
from app.clients.services.impact_preview_service import compute_creation_impact
from app.common.enums import AdvancePaymentFrequency, EntityType, IdNumberType, VatType
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline
from app.tax_deadline.services import deadline_generator
from app.vat_reports.models.vat_work_item import VatWorkItem


def test_preview_impact_returns_backend_vat_exempt_ceiling(client, advisor_headers):
    response = client.post(
        "/api/v1/clients/preview-impact",
        headers=advisor_headers,
        json={"client": {"entity_type": "osek_patur"}},
    )

    assert response.status_code == 200
    year = date.today().year
    expected = Decimal(str(get_financial(year, "osek_patur_ceiling_ils").value))
    expected = str(expected.quantize(Decimal("0.01")))
    assert response.json()["vat_exempt_ceiling"] == expected


def test_preview_impact_matches_actual_future_deadline_generation(test_db, monkeypatch):
    reference_date = date(2026, 4, 30)
    monkeypatch.setattr(deadline_generator, "_today", lambda: reference_date)

    preview = compute_creation_impact(
        entity_type=EntityType.OSEK_MURSHE,
        vat_reporting_frequency=VatType.MONTHLY,
        advance_payment_frequency=AdvancePaymentFrequency.MONTHLY,
        reference_date=reference_date,
        advance_rate=Decimal("5.0"),
    )
    counts = {item.label: item.count for item in preview.items}

    client_record = ClientCreationService(test_db).create_client(
        full_name="Preview Match Client",
        id_number="123456780",
        id_number_type=IdNumberType.INDIVIDUAL,
        entity_type=EntityType.OSEK_MURSHE,
        vat_reporting_frequency=VatType.MONTHLY,
        advance_payment_frequency=AdvancePaymentFrequency.MONTHLY,
        advance_rate=Decimal("5.0"),
        actor_id=1,
    )
    deadlines = (
        test_db.query(TaxDeadline)
        .filter(TaxDeadline.client_record_id == client_record.id)
        .all()
    )
    vat_work_items_count = test_db.query(VatWorkItem).filter(
        VatWorkItem.client_record_id == client_record.id
    ).count()
    advance_payments_count = test_db.query(AdvancePayment).filter(
        AdvancePayment.client_record_id == client_record.id
    ).count()
    reports_count = test_db.query(AnnualReport).filter(
        AnnualReport.client_record_id == client_record.id
    ).count()
    binders_count = test_db.query(Binder).filter(Binder.client_record_id == client_record.id).count()

    actual_counts = {
        "קלסר פעיל": binders_count,
        "מועדי מע\"מ": sum(d.deadline_type == DeadlineType.VAT for d in deadlines),
        "תיקי מע\"מ": vat_work_items_count,
        "מועדי מקדמות": sum(d.deadline_type == DeadlineType.ADVANCE_PAYMENT for d in deadlines),
        "רשומות מקדמות": advance_payments_count,
        "מועד הגשת דוח שנתי": sum(d.deadline_type == DeadlineType.ANNUAL_REPORT for d in deadlines),
        "תיק דוח שנתי": reports_count,
    }
    assert actual_counts == {
        "קלסר פעיל": 1,
        "מועדי מע\"מ": 9,
        "תיקי מע\"מ": 9,
        "מועדי מקדמות": 9,
        "רשומות מקדמות": 9,
        "מועד הגשת דוח שנתי": 1,
        "תיק דוח שנתי": 1,
    }
    assert counts == actual_counts
