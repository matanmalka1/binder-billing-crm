from app.businesses.models.business_tax_profile import BusinessTaxProfile, VatType
from tests.tax_deadline.factories import create_business


def test_generate_deadlines_endpoint_success(client, test_db, advisor_headers):
    business = create_business(test_db, name_prefix="API Generate")
    profile = BusinessTaxProfile(business_id=business.id, vat_type=VatType.MONTHLY)
    test_db.add(profile)
    test_db.commit()

    resp = client.post(
        "/api/v1/tax-deadlines/generate",
        headers=advisor_headers,
        json={"business_id": business.id, "year": 2026},
    )

    assert resp.status_code == 201
    assert resp.json()["created_count"] == 25


def test_generate_deadlines_endpoint_advisor_only(client, test_db, secretary_headers):
    business = create_business(test_db, name_prefix="API Generate Sec")

    resp = client.post(
        "/api/v1/tax-deadlines/generate",
        headers=secretary_headers,
        json={"business_id": business.id, "year": 2026},
    )

    assert resp.status_code == 403
