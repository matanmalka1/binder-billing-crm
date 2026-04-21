from io import BytesIO
from datetime import date

from tests.helpers.identity import seed_business, seed_client_identity


def _create_client(db):
    return seed_client_identity(
        db,
        full_name="Docs Client",
        id_number="DOC-001",
    )


def _create_business(db, crm_client):
    business = seed_business(
        db,
        legal_entity_id=crm_client.legal_entity_id,
        business_name="Docs Client Business",
        opened_at=date.today(),
    )
    db.commit()
    db.refresh(business)
    business.client_id = crm_client.id
    return business


def test_document_download_and_replace(client, test_db, advisor_headers):
    crm_client = _create_client(test_db)
    business = _create_business(test_db, crm_client)

    upload_resp = client.post(
        "/api/v1/documents/upload",
        headers=advisor_headers,
        files={"file": ("id.pdf", BytesIO(b"orig"), "application/pdf")},
        data={"client_record_id": crm_client.id, "business_id": business.id, "document_type": "id_copy"},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    download_resp = client.get(f"/api/v1/documents/{doc_id}/download-url", headers=advisor_headers)
    assert download_resp.status_code == 200
    assert "url" in download_resp.json()

    replace_resp = client.put(
        f"/api/v1/documents/{doc_id}/replace",
        headers=advisor_headers,
        files={"file": ("id-new.pdf", BytesIO(b"new"), "application/pdf")},
    )
    assert replace_resp.status_code == 200
    replaced = replace_resp.json()
    assert replaced["id"] == doc_id
    assert replaced["is_present"] is True
