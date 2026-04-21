"""Service: export VAT client data to Excel or PDF."""

from __future__ import annotations

import os
import tempfile
from typing import Dict

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.vat_reports.repositories.vat_client_summary_repository import VatClientSummaryRepository
from app.vat_reports.schemas.vat_client_summary_schema import VatPeriodRow
from app.vat_reports.services.messages import VAT_CLIENT_NOT_FOUND
from app.vat_reports.services.vat_export_excel import export_vat_to_excel
from app.vat_reports.services.vat_export_pdf import export_vat_to_pdf


def _get_export_dir() -> str:
    path = os.path.join(tempfile.gettempdir(), "exports")
    os.makedirs(path, exist_ok=True)
    return path


def _load(db: Session, client_record_id: int, year: int):
    client_record = ClientRecordRepository(db).get_by_id(client_record_id)
    if not client_record:
        raise NotFoundError(VAT_CLIENT_NOT_FOUND.format(client_record_id=client_record_id), "VAT.NOT_FOUND")
    legal_entity = LegalEntityRepository(db).get_by_id(client_record.legal_entity_id)
    display_name = legal_entity.official_name if legal_entity else f"לקוח #{client_record_id}"
    all_periods = VatClientSummaryRepository(db).get_periods_for_client(client_record_id)
    periods = [
        VatPeriodRow.model_validate(work_item)
        for work_item, *_ in all_periods
        if work_item.period.startswith(str(year))
    ]
    return display_name, periods


def export_to_excel(db: Session, client_record_id: int, year: int) -> Dict[str, object]:
    display_name, periods = _load(db, client_record_id, year)
    return export_vat_to_excel(display_name, client_record_id, year, periods, _get_export_dir())


def export_to_pdf(db: Session, client_record_id: int, year: int) -> Dict[str, object]:
    display_name, periods = _load(db, client_record_id, year)
    return export_vat_to_pdf(display_name, client_record_id, year, periods, _get_export_dir())


_MEDIA_TYPES = {
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def export(db: Session, client_record_id: int, year: int, fmt: str) -> tuple[Dict[str, object], str]:
    """Dispatch export by format. Returns (result_dict, media_type)."""
    if fmt == "excel":
        result = export_to_excel(db, client_record_id, year)
    else:
        result = export_to_pdf(db, client_record_id, year)
    return result, _MEDIA_TYPES[fmt]
