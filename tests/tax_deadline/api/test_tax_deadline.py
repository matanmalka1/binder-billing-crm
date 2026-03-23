from datetime import date, timedelta

from app.tax_deadline.api.tax_deadline import _build_response
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from tests.tax_deadline.factories import create_business


def test_create_and_get_tax_deadline(client, test_db, advisor_headers):
    business = create_business(test_db, name_prefix="API CRUD")
    due = date.today() + timedelta(days=10)

    create = client.post(
        "/api/v1/tax-deadlines",
        headers=advisor_headers,
        json={
            "business_id": business.id,
            "deadline_type": "vat",
            "due_date": due.isoformat(),
            "payment_amount": 1500.5,
            "description": "VAT filing",
        },
    )
    assert create.status_code == 201
    payload = create.json()
    deadline_id = payload["id"]
    assert payload["deadline_type"] == "vat"
    assert payload["status"] == "pending"

    fetched = client.get(f"/api/v1/tax-deadlines/{deadline_id}", headers=advisor_headers)
    assert fetched.status_code == 200
    assert float(fetched.json()["payment_amount"]) == 1500.5


def test_complete_update_delete_and_query_filters(client, test_db, advisor_headers):
    business_a = create_business(test_db, name_prefix="API A")
    business_b = create_business(test_db, name_prefix="API B")
    repo = TaxDeadlineRepository(test_db)

    deadline = repo.create(
        business_id=business_a.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=3),
    )

    complete = client.post(f"/api/v1/tax-deadlines/{deadline.id}/complete", headers=advisor_headers)
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"
    assert complete.json()["completed_at"] is not None

    update = client.put(
        f"/api/v1/tax-deadlines/{deadline.id}",
        headers=advisor_headers,
        json={"deadline_type": "annual_report", "payment_amount": 200.5, "description": "Updated"},
    )
    assert update.status_code == 200
    assert update.json()["deadline_type"] == "annual_report"
    assert float(update.json()["payment_amount"]) == 200.5

    repo.create(
        business_id=business_a.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=2),
    )
    repo.create(
        business_id=business_b.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=2),
    )

    filtered = client.get(
        f"/api/v1/tax-deadlines?business_id={business_a.id}&deadline_type=vat",
        headers=advisor_headers,
    )
    assert filtered.status_code == 200
    assert all(item["business_id"] == business_a.id for item in filtered.json()["items"])

    deleted = client.delete(f"/api/v1/tax-deadlines/{deadline.id}", headers=advisor_headers)
    assert deleted.status_code == 204


def test_update_without_fields_returns_400(client, test_db, advisor_headers):
    business = create_business(test_db, name_prefix="API NoFields")
    repo = TaxDeadlineRepository(test_db)
    deadline = repo.create(
        business_id=business.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=10),
    )

    resp = client.put(f"/api/v1/tax-deadlines/{deadline.id}", headers=advisor_headers, json={})
    assert resp.status_code == 400
    assert resp.json()["error"] == "TAX_DEADLINE.NO_FIELDS_PROVIDED"


def test_list_by_client_name_and_build_response_business_name(client, test_db, advisor_headers):
    business = create_business(test_db, name_prefix="Client Name Filter")
    repo = TaxDeadlineRepository(test_db)
    deadline = repo.create(
        business_id=business.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=2),
    )

    resp = client.get(
        "/api/v1/tax-deadlines?client_name=Client%20Name%20Filter",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == deadline.id
    assert items[0]["business_name"].startswith("Client Name Filter")

    built = _build_response(deadline, business_name="Manual Name")
    assert built.business_name == "Manual Name"


def test_list_tax_deadlines_enriches_fallback_business_name_for_sole_proprietor(
    client, test_db, advisor_headers,
):
    business = create_business(test_db, name_prefix="Sole Prop")
    repo = TaxDeadlineRepository(test_db)
    deadline = repo.create(
        business_id=business.id,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
        due_date=date.today() + timedelta(days=1),
    )

    resp = client.get("/api/v1/tax-deadlines", headers=advisor_headers)
    assert resp.status_code == 200

    item = next((row for row in resp.json()["items"] if row["id"] == deadline.id), None)
    assert item is not None
    assert item["business_id"] == business.id
    assert item["business_name"] == business.full_name
