"""Service: export VAT client data to Excel or PDF."""

from __future__ import annotations

import os
import tempfile
from typing import Dict

from sqlalchemy.orm import Session

from app.clients.repositories.client_repository import ClientRepository
from app.vat_reports.repositories.vat_client_summary_repository import (
    VatClientSummaryRepository,
)
from app.vat_reports.services.vat_export_excel import export_vat_to_excel
from app.vat_reports.services.vat_export_pdf import export_vat_to_pdf


def _get_export_dir() -> str:
    path = os.path.join(tempfile.gettempdir(), "exports")
    os.makedirs(path, exist_ok=True)
    return path


def _load(db: Session, client_id: int, year: int):
    client = ClientRepository(db).get_by_id(client_id)
    if not client:
        raise ValueError(f"לקוח {client_id} לא נמצא")
    all_periods = VatClientSummaryRepository(db).get_periods_for_client(client_id)
    periods = [p for p in all_periods if p.period.startswith(str(year))]
    return client.full_name, periods


def export_to_excel(db: Session, client_id: int, year: int) -> Dict[str, object]:
    client_name, periods = _load(db, client_id, year)
    return export_vat_to_excel(client_name, client_id, year, periods, _get_export_dir())


def export_to_pdf(db: Session, client_id: int, year: int) -> Dict[str, object]:
    client_name, periods = _load(db, client_id, year)
    return export_vat_to_pdf(client_name, client_id, year, periods, _get_export_dir())
