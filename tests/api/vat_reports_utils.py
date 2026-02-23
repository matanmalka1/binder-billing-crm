def create_work_item(client, headers, vat_client, period):
    response = client.post(
        "/api/v1/vat/work-items",
        headers=headers,
        json={"client_id": vat_client.id, "period": period},
    )
    assert response.status_code == 201
    return response.json()["id"]


def income_payload(
    invoice_number="INV-001",
    invoice_date="2026-01-15T00:00:00",
    counterparty_name="Customer A",
    net_amount="1000.00",
    vat_amount="170.00",
):
    return {
        "invoice_type": "income",
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "counterparty_name": counterparty_name,
        "net_amount": net_amount,
        "vat_amount": vat_amount,
    }


def add_income_invoice(client, headers, item_id, payload=None):
    response = client.post(
        f"/api/v1/vat/work-items/{item_id}/invoices",
        headers=headers,
        json=payload or income_payload(),
    )
    assert response.status_code == 201
    return response.json()


def setup_ready_item(client, headers, vat_client, period):
    item_id = create_work_item(client, headers, vat_client, period)
    add_income_invoice(client, headers, item_id)
    client.post(f"/api/v1/vat/work-items/{item_id}/ready-for-review", headers=headers)
    return item_id
