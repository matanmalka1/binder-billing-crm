from datetime import date
from decimal import Decimal

from tax_rules import get_financial

from app.clients.services.client_creation_service import ClientCreationService
from app.clients.services.impact_preview_service import compute_creation_impact
from app.common.enums import EntityType, IdNumberType, VatType
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline
from app.tax_deadline.services import deadline_generator


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
        advance_rate=Decimal("5.0"),
        actor_id=1,
    )
    deadlines = (
        test_db.query(TaxDeadline)
        .filter(TaxDeadline.client_record_id == client_record.id)
        .all()
    )

    actual_counts = {
        "מועדי מע\"מ": sum(d.deadline_type == DeadlineType.VAT for d in deadlines),
        "מועדי מקדמות": sum(d.deadline_type == DeadlineType.ADVANCE_PAYMENT for d in deadlines),
        "מועד הגשת דוח שנתי": sum(d.deadline_type == DeadlineType.ANNUAL_REPORT for d in deadlines),
    }
    assert actual_counts == {
        "מועדי מע\"מ": 9,
        "מועדי מקדמות": 9,
        "מועד הגשת דוח שנתי": 1,
    }
    assert counts["מועדי מע\"מ"] == actual_counts["מועדי מע\"מ"]
    assert counts["מועדי מקדמות"] == actual_counts["מועדי מקדמות"]
    assert counts["מועד הגשת דוח שנתי"] == actual_counts["מועד הגשת דוח שנתי"]
