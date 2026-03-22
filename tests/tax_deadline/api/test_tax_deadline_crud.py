from datetime import date, timedelta

from tests.tax_deadline.factories import create_business


def test_tax_deadline_full_crud_flow(client, test_db, advisor_headers):
    business = create_business(test_db, name_prefix="API Full")
    due_date = date.today() + timedelta(days=3)

    create_resp = client.post(
        "/api/v1/tax-deadlines",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "deadline_type": "vat",
            "due_date": due_date.isoformat(),
            "payment_amount": 150.0,
            "description": "VAT payment",
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    deadline_id = created["id"]

    list_resp = client.get("/api/v1/tax-deadlines", headers=advisor_headers)
    assert list_resp.status_code == 200
    listed_ids = {item["id"] for item in list_resp.json()["items"]}
    assert deadline_id in listed_ids

    get_resp = client.get(f"/api/v1/tax-deadlines/{deadline_id}", headers=advisor_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["business_id"] == business.id

    update_resp = client.put(
        f"/api/v1/tax-deadlines/{deadline_id}",
        headers=advisor_headers,
        json={"payment_amount": 175.5, "description": "Updated VAT"},
    )
    assert update_resp.status_code == 200
    assert float(update_resp.json()["payment_amount"]) == 175.5

    complete_resp = client.post(f"/api/v1/tax-deadlines/{deadline_id}/complete", headers=advisor_headers)
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"

    delete_resp = client.delete(f"/api/v1/tax-deadlines/{deadline_id}", headers=advisor_headers)
    assert delete_resp.status_code == 204

    not_found = client.get(f"/api/v1/tax-deadlines/{deadline_id}", headers=advisor_headers)
    assert not_found.status_code == 404
