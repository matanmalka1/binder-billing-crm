from datetime import date

from app.clients.services.client_creation_service import ClientCreationService
from app.common.enums import AdvancePaymentFrequency, EntityType, IdNumberType, VatType


def test_grouped_api_returns_monthly_advance_payment_groups(
    client,
    test_db,
    advisor_headers,
):
    ClientCreationService(test_db).create_client(
        full_name="חומוס אחלה",
        id_number="515555555",
        id_number_type=IdNumberType.CORPORATION,
        entity_type=EntityType.COMPANY_LTD,
        vat_reporting_frequency=VatType.MONTHLY,
        advance_payment_frequency=AdvancePaymentFrequency.MONTHLY,
        actor_id=1,
        reference_date=date(2026, 5, 7),
    )

    response = client.get(
        "/api/v1/tax-deadlines/grouped",
        headers=advisor_headers,
        params={
            "deadline_type": "advance_payment",
            "due_from": "2026-05-07",
            "due_to": "2027-01-15",
        },
    )

    assert response.status_code == 200
    groups = response.json()["groups"]
    periods = [
        (group["period"], group["period_months_count"])
        for group in groups
        if group["deadline_type"] == "advance_payment"
    ]

    assert periods == [(f"2026-{month:02d}", 1) for month in range(4, 13)]
