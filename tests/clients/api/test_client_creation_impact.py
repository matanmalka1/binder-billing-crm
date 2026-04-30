from datetime import date
from decimal import Decimal

from tax_rules import get_financial


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
