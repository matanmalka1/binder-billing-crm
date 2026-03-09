from datetime import date
import io

import openpyxl

from app.clients.models.client import Client, ClientType
from app.clients.repositories.client_repository import ClientRepository

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _seed_clients(db):
    clients = [
        Client(
            full_name="Export One",
            id_number="C-EXPORT-1",
            client_type=ClientType.COMPANY,
            opened_at=date.today(),
        ),
        Client(
            full_name="Export Two",
            id_number="C-EXPORT-2",
            client_type=ClientType.OSEK_PATUR,
            opened_at=date.today(),
        ),
    ]
    db.add_all(clients)
    db.commit()
    for client in clients:
        db.refresh(client)
    return clients


def test_clients_export_returns_excel_file(client, test_db, advisor_headers):
    seeded = _seed_clients(test_db)

    resp = client.get("/api/v1/clients/export", headers=advisor_headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(EXCEL_MEDIA_TYPE)
    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    ws = wb.active

    assert ws.cell(row=1, column=1).value == "ID"
    exported_names = {ws.cell(row=i, column=2).value for i in range(2, ws.max_row + 1)}
    assert {c.full_name for c in seeded}.issubset(exported_names)


def test_clients_template_download(client, advisor_headers):
    resp = client.get("/api/v1/clients/template", headers=advisor_headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(EXCEL_MEDIA_TYPE)
    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    ws = wb.active

    assert ws.cell(row=1, column=1).value == "Full Name"
    assert ws.cell(row=2, column=1).value  # sample row present


def test_clients_import_creates_clients(client, test_db, advisor_headers):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["full_name", "id_number", "client_type", "phone", "email", "notes"])
    ws.append(["Import A", "C-IMPORT-1", "company", "0501111111", "a@example.com", ""])
    ws.append(["Import B", "C-IMPORT-2", "osek_murshe", "", "b@example.com", "note"])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    resp = client.post(
        "/api/v1/clients/import",
        headers=advisor_headers,
        files={"file": ("clients.xlsx", buffer.getvalue(), EXCEL_MEDIA_TYPE)},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 2
    assert data["total_rows"] == 2
    assert data["errors"] == []

    repo = ClientRepository(test_db)
    assert repo.count() >= 2
