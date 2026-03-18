from datetime import date

from app.clients.models import Client, ClientType


def _client(test_db):
    c = Client(
        full_name="Charge API Extra",
        id_number="CAE001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


def test_get_charge_as_advisor_and_delete_paths(client, advisor_headers, test_db):
    c = _client(test_db)
    create = client.post(
        "/api/v1/charges",
        headers=advisor_headers,
        json={"client_id": c.id, "amount": 100.0, "charge_type": "one_time"},
    )
    assert create.status_code == 201
    charge_id = create.json()["id"]

    get_adv = client.get(f"/api/v1/charges/{charge_id}", headers=advisor_headers)
    assert get_adv.status_code == 200
    assert "amount" in get_adv.json()

    delete_ok = client.delete(f"/api/v1/charges/{charge_id}", headers=advisor_headers)
    assert delete_ok.status_code == 204

    delete_missing = client.delete("/api/v1/charges/999999", headers=advisor_headers)
    assert delete_missing.status_code == 404
