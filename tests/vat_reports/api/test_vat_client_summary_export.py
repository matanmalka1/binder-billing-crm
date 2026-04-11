from datetime import datetime
from decimal import Decimal
import io

import openpyxl
import pytest

from app.common.enums import VatType
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _seed_work_items(db, client_id: int, created_by: int):
    items = [
        VatWorkItem(
            client_id=client_id,
            created_by=created_by,
            period="2026-02",
            period_type=VatType.MONTHLY,
            status=VatWorkItemStatus.READY_FOR_REVIEW,
            total_output_vat=Decimal("1500.00"),
            total_input_vat=Decimal("500.00"),
            net_vat=Decimal("1000.00"),
            total_output_net=Decimal("0.00"),
            total_input_net=Decimal("0.00"),
            final_vat_amount=None,
        ),
        VatWorkItem(
            client_id=client_id,
            created_by=created_by,
            period="2026-01",
            period_type=VatType.MONTHLY,
            status=VatWorkItemStatus.FILED,
            total_output_vat=Decimal("800.00"),
            total_input_vat=Decimal("200.00"),
            net_vat=Decimal("600.00"),
            total_output_net=Decimal("0.00"),
            total_input_net=Decimal("0.00"),
            final_vat_amount=Decimal("600.00"),
            filed_at=datetime(2026, 2, 15),
            filed_by=created_by,
        ),
    ]
    db.add_all(items)
    db.commit()
    for item in items:
        db.refresh(item)
    return items


def test_vat_client_summary_returns_periods_and_annual(client, test_db, advisor_headers, vat_client, test_user):
    _seed_work_items(test_db, vat_client.id, test_user.id)

    resp = client.get(f"/api/v1/vat/clients/{vat_client.id}/summary", headers=advisor_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["client_id"] == vat_client.id
    assert [row["period"] for row in payload["periods"]] == ["2026-02", "2026-01"]
    assert len(payload["annual"]) == 1
    assert payload["annual"][0]["year"] == 2026
    assert float(payload["annual"][0]["total_output_vat"]) == 2300.0
    assert float(payload["annual"][0]["total_input_vat"]) == 700.0
    assert float(payload["annual"][0]["net_vat"]) == 1600.0
    assert payload["annual"][0]["periods_count"] == 2
    assert payload["annual"][0]["filed_count"] == 1


def test_vat_client_work_items_endpoint(client, test_db, advisor_headers, vat_client, test_user):
    _seed_work_items(test_db, vat_client.id, test_user.id)

    resp = client.get(
        f"/api/v1/vat/clients/{vat_client.id}/work-items",
        headers=advisor_headers,
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 2
    assert payload["items"][0]["period"] == "2026-02"
    assert payload["items"][1]["period"] == "2026-01"
    assert payload["items"][0]["client_name"] == vat_client.full_name
    assert payload["items"][1]["filed_by_name"] == test_user.full_name


def test_vat_client_export_excel(client, test_db, advisor_headers, vat_client, test_user):
    _seed_work_items(test_db, vat_client.id, test_user.id)

    resp = client.get(
        f"/api/v1/vat/clients/{vat_client.id}/export?format=excel&year=2026",
        headers=advisor_headers,
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(EXCEL_MEDIA_TYPE)

    workbook = openpyxl.load_workbook(io.BytesIO(resp.content))
    sheet = workbook.active
    assert sheet["A1"].value is not None
    assert sheet["A4"].value == "2026-02"


def test_vat_client_export_pdf_service_error_returns_500(client, advisor_headers, vat_client, monkeypatch):
    monkeypatch.setattr(
        "app.vat_reports.api.routes_business_summary.export",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )

    with pytest.raises(RuntimeError, match="fail"):
        client.get(
            f"/api/v1/vat/clients/{vat_client.id}/export?format=pdf&year=2026",
            headers=advisor_headers,
        )


def test_vat_client_export_import_error_returns_detail(client, advisor_headers, vat_client, monkeypatch):
    monkeypatch.setattr(
        "app.vat_reports.api.routes_business_summary.export",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ImportError("openpyxl missing")),
    )

    with pytest.raises(ImportError, match="openpyxl missing"):
        client.get(
            f"/api/v1/vat/clients/{vat_client.id}/export?format=excel&year=2026",
            headers=advisor_headers,
        )
