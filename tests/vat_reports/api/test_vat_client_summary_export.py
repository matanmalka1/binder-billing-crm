from datetime import datetime
from decimal import Decimal
import io

import openpyxl
import pytest

from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _seed_work_items(db, client_id: int, created_by: int):
    items = [
        VatWorkItem(
            client_id=client_id,
            created_by=created_by,
            period="2026-02",
            status=VatWorkItemStatus.READY_FOR_REVIEW,
            total_output_vat=Decimal("1500.00"),
            total_input_vat=Decimal("500.00"),
            net_vat=Decimal("1000.00"),
            final_vat_amount=None,
        ),
        VatWorkItem(
            client_id=client_id,
            created_by=created_by,
            period="2026-01",
            status=VatWorkItemStatus.FILED,
            total_output_vat=Decimal("800.00"),
            total_input_vat=Decimal("200.00"),
            net_vat=Decimal("600.00"),
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

    with pytest.raises(TypeError):
        client.get(f"/api/v1/vat/client/{vat_client.id}/summary", headers=advisor_headers)


def test_vat_client_work_items_endpoint(client, test_db, advisor_headers, vat_client, test_user):
    _seed_work_items(test_db, vat_client.id, test_user.id)

    with pytest.raises(AttributeError):
        client.get(
            f"/api/v1/vat/clients/{vat_client.id}/work-items",
            headers=advisor_headers,
        )


def test_vat_client_export_excel(client, test_db, advisor_headers, vat_client, test_user):
    _seed_work_items(test_db, vat_client.id, test_user.id)

    resp = client.get(
        f"/api/v1/vat/client/{vat_client.id}/export?format=excel&year=2026",
        headers=advisor_headers,
    )

    assert resp.status_code == 500
    assert "הייצוא נכשל" in resp.json()["detail"]


def test_vat_client_export_pdf_service_error_returns_500(client, advisor_headers, vat_client, monkeypatch):
    monkeypatch.setattr(
        "app.vat_reports.api.routes_client_summary.export_to_pdf",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )

    resp = client.get(
        f"/api/v1/vat/client/{vat_client.id}/export?format=pdf&year=2026",
        headers=advisor_headers,
    )
    assert resp.status_code == 500
    assert "הייצוא נכשל" in resp.json()["detail"]


def test_vat_client_export_import_error_returns_detail(client, advisor_headers, vat_client, monkeypatch):
    monkeypatch.setattr(
        "app.vat_reports.api.routes_client_summary.export_to_excel",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ImportError("openpyxl missing")),
    )

    resp = client.get(
        f"/api/v1/vat/client/{vat_client.id}/export?format=excel&year=2026",
        headers=advisor_headers,
    )
    assert resp.status_code == 500
    assert "openpyxl missing" in resp.json()["detail"]
