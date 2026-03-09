from io import BytesIO
from itertools import count
from datetime import date

from app.clients.models import Client, ClientType
from app.permanent_documents.models.permanent_document import DocumentType
from app.permanent_documents.repositories.permanent_document_repository import PermanentDocumentRepository


_client_seq = count(1)


def _client(db) -> Client:
    c = Client(
        full_name=f"PermDoc Client {next(_client_seq)}",
        id_number=f"88888888{next(_client_seq)}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_upload_and_list_documents(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    file_bytes = BytesIO(b"content")

    resp = client.post(
        "/api/v1/documents/upload",
        headers=advisor_headers,
        files={"file": ("id.pdf", file_bytes, "application/pdf")},
        data={"client_id": crm_client.id, "document_type": "id_copy"},
    )
    assert resp.status_code == 201
    doc = resp.json()
    assert doc["client_id"] == crm_client.id
    assert doc["document_type"] == "id_copy"
    assert doc["is_present"] is True
    doc_id = doc["id"]

    list_resp = client.get(f"/api/v1/documents/client/{crm_client.id}", headers=advisor_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == doc_id


def test_get_download_url_and_replace_document(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    repo = PermanentDocumentRepository(test_db)
    # Seed a document directly
    doc = repo.create(
        client_id=crm_client.id,
        document_type=DocumentType.ID_COPY,
        storage_key="clients/x/id_copy/original.pdf",
        uploaded_by=1,
    )

    url_resp = client.get(f"/api/v1/documents/{doc.id}/download-url", headers=advisor_headers)
    assert url_resp.status_code == 200
    assert "url" in url_resp.json()

    replace_resp = client.put(
        f"/api/v1/documents/{doc.id}/replace",
        headers=advisor_headers,
        files={"file": ("new.pdf", BytesIO(b"new"), "application/pdf")},
    )
    assert replace_resp.status_code == 200
    replaced = replace_resp.json()
    assert replaced["id"] == doc.id
    assert replaced["is_present"] is True


def test_delete_document_marks_deleted(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    repo = PermanentDocumentRepository(test_db)
    doc = repo.create(
        client_id=crm_client.id,
        document_type=DocumentType.POWER_OF_ATTORNEY,
        storage_key="clients/x/power_of_attorney/doc.pdf",
        uploaded_by=1,
    )

    del_resp = client.delete(f"/api/v1/documents/{doc.id}", headers=advisor_headers)
    assert del_resp.status_code == 204

    # Soft-deleted doc is hidden from list
    list_resp = client.get(f"/api/v1/documents/client/{crm_client.id}", headers=advisor_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["items"] == []
