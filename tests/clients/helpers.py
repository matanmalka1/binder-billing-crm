class CreateClientResponse:
    def __init__(self, response):
        self._response = response
        self.status_code = response.status_code

    def json(self):
        payload = self._response.json()
        return payload["client"] if self.status_code == 201 else payload


def make_client_create_payload(
    *,
    full_name="Test Client",
    id_number="000000000",
    id_number_type="corporation",
    business_name=None,
    opened_at="2026-04-19",
    **client_overrides,
):
    client_payload = {
        "full_name": full_name,
        "id_number": id_number,
        "id_number_type": id_number_type,
        "entity_type": "company_ltd",
        "phone": "050-1234567",
        "email": "test@example.com",
        "address_street": "Main",
        "address_building_number": "10",
        "address_apartment": "5",
        "address_city": "Tel Aviv",
        "address_zip_code": "1234567",
        "vat_reporting_frequency": "monthly",
        "advance_rate": "8.5",
        "accountant_name": "CPA Name",
    }
    client_payload.update(client_overrides)
    return {
        "client": client_payload,
        "business": {
            "business_name": business_name or f"{full_name} Business",
            "opened_at": opened_at,
        },
    }


def create_client_via_api(client, headers, **payload_overrides):
    response = client.post(
        "/api/v1/clients",
        headers=headers,
        json=make_client_create_payload(**payload_overrides),
    )
    return CreateClientResponse(response)
