import io
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from openpyxl import Workbook
from starlette.datastructures import UploadFile

from app.clients.api import clients_excel as clients_excel_api

IDEMPOTENCY_HEADER = {"X-Idempotency-Key": "clients-import-test-key"}


def _workbook_bytes(rows: list[list[str | None]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def test_export_clients_excel(client, advisor_headers):
    response = client.get("/api/v1/clients/export", headers=advisor_headers)

    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
    assert "attachment; filename=" in response.headers.get("content-disposition", "")


def test_template_download(client, advisor_headers):
    response = client.get("/api/v1/clients/template", headers=advisor_headers)

    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]


def test_import_clients_excel_advisor_only(client, advisor_headers, secretary_headers):
    payload = _workbook_bytes([
        ["full_name", "business_name", "id_number", "phone", "email"],
        ["Excel User", "Excel User Business", "710000001", "0500000000", "excel@example.com"],
    ])

    denied = client.post(
        "/api/v1/clients/import",
        headers={**secretary_headers, **IDEMPOTENCY_HEADER},
        files={"file": ("clients.xlsx", payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert denied.status_code == 403

    ok = client.post(
        "/api/v1/clients/import",
        headers={**advisor_headers, **IDEMPOTENCY_HEADER},
        files={"file": ("clients.xlsx", payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["created"] == 1
    assert body["total_rows"] == 1
    assert body["errors"] == []


def test_import_clients_excel_returns_row_errors(client, advisor_headers):
    payload = _workbook_bytes([
        ["full_name", "business_name", "id_number", "phone", "email"],
        ["", "", "", None, None],
        ["Duplicate One", "Duplicate One Business", "720000001", None, None],
        ["Duplicate Two", "Duplicate Two Business", "720000001", None, None],
    ])

    response = client.post(
        "/api/v1/clients/import",
        headers={**advisor_headers, **IDEMPOTENCY_HEADER},
        files={"file": ("clients.xlsx", payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1
    assert body["total_rows"] == 3
    assert len(body["errors"]) == 1
    assert {err["row"] for err in body["errors"]} == {4}


def test_import_clients_excel_rejects_large_content_length(client, advisor_headers):
    payload = _workbook_bytes([["full_name", "business_name", "id_number"], ["Big", "Big Business", "730000001"]])

    response = client.post(
        "/api/v1/clients/import",
        headers={
            **advisor_headers,
            **IDEMPOTENCY_HEADER,
            "Content-Length": str(11 * 1024 * 1024),
        },
        files={"file": ("clients.xlsx", payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 413


def test_import_clients_excel_invalid_file(client, advisor_headers):
    response = client.post(
        "/api/v1/clients/import",
        headers={**advisor_headers, **IDEMPOTENCY_HEADER},
        files={"file": ("bad.xlsx", b"not-an-excel", "application/octet-stream")},
    )

    assert response.status_code == 400


def test_export_clients_excel_handles_service_import_error(client, advisor_headers, monkeypatch):
    monkeypatch.setattr(
        clients_excel_api.ClientExcelService,
        "export_clients",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ImportError("missing dependency")),
    )

    response = client.get("/api/v1/clients/export", headers=advisor_headers)

    assert response.status_code == 500
    assert response.json()["detail"] == "missing dependency"


def test_template_download_handles_service_import_error(client, advisor_headers, monkeypatch):
    monkeypatch.setattr(
        clients_excel_api.ClientExcelService,
        "generate_template",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ImportError("missing template dependency")),
    )

    response = client.get("/api/v1/clients/template", headers=advisor_headers)

    assert response.status_code == 500
    assert response.json()["detail"] == "missing template dependency"


def test_import_clients_excel_rejects_large_body_without_content_length(client, advisor_headers, monkeypatch):
    monkeypatch.setattr(clients_excel_api, "MAX_UPLOAD_SIZE", 32)
    payload = b"x" * 40

    response = client.post(
        "/api/v1/clients/import",
        headers={**advisor_headers, **IDEMPOTENCY_HEADER},
        files={"file": ("clients.xlsx", payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 413


def test_import_clients_excel_openpyxl_missing_returns_500(client, advisor_headers, monkeypatch):
    original_import = __import__

    def _import(name, *args, **kwargs):
        if name == "openpyxl":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _import)
    payload = _workbook_bytes([
        ["full_name", "business_name", "id_number"],
        ["Openpyxl Missing", "Openpyxl Missing Business", "740000001"],
    ])

    response = client.post(
        "/api/v1/clients/import",
        headers={**advisor_headers, **IDEMPOTENCY_HEADER},
        files={"file": ("clients.xlsx", payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 500
    assert "openpyxl" in response.json()["detail"]


def test_import_clients_excel_rejects_large_body_after_read_without_content_length(monkeypatch, test_db):
    monkeypatch.setattr(clients_excel_api, "MAX_UPLOAD_SIZE", 8)
    file_obj = UploadFile(filename="clients.xlsx", file=io.BytesIO(b"0123456789"))
    request = SimpleNamespace(headers={})
    user = SimpleNamespace(id=1)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            clients_excel_api.import_clients_from_excel(
                file=file_obj,
                request=request,
                db=test_db,
                user=user,
                _x_idempotency_key="direct-call-key",
            )
        )

    assert exc.value.status_code == 413


def test_import_clients_excel_requires_idempotency_key(client, advisor_headers):
    payload = _workbook_bytes([
        ["full_name", "business_name", "id_number"],
        ["Missing Key", "Missing Key Business", "770000001"],
    ])

    response = client.post(
        "/api/v1/clients/import",
        headers=advisor_headers,
        files={"file": ("clients.xlsx", payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 422
