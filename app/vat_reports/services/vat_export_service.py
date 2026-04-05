"""Service: export VAT business data to Excel or PDF."""

from __future__ import annotations

import os
import tempfile
from typing import Dict

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.businesses.repositories.business_repository import BusinessRepository
from app.vat_reports.repositories.vat_client_summary_repository import VatClientSummaryRepository
from app.vat_reports.schemas.vat_client_summary_schema import VatPeriodRow
from app.vat_reports.services.vat_export_excel import export_vat_to_excel
from app.vat_reports.services.vat_export_pdf import export_vat_to_pdf


def _get_export_dir() -> str:
    path = os.path.join(tempfile.gettempdir(), "exports")
    os.makedirs(path, exist_ok=True)
    return path


def _load(db: Session, business_id: int, year: int):
    business = BusinessRepository(db).get_by_id(business_id)
    if not business:
        raise NotFoundError(f"עסק {business_id} לא נמצא", "VAT.NOT_FOUND")
    display_name = business.business_name or business.client.full_name
    all_periods = VatClientSummaryRepository(db).get_periods_for_business(business_id)
    periods = [
        VatPeriodRow.model_validate(work_item)
        for work_item, *_ in all_periods
        if work_item.period.startswith(str(year))
    ]
    return display_name, periods


def export_to_excel(db: Session, business_id: int, year: int) -> Dict[str, object]:
    display_name, periods = _load(db, business_id, year)
    return export_vat_to_excel(display_name, business_id, year, periods, _get_export_dir())


def export_to_pdf(db: Session, business_id: int, year: int) -> Dict[str, object]:
    display_name, periods = _load(db, business_id, year)
    return export_vat_to_pdf(display_name, business_id, year, periods, _get_export_dir())


_MEDIA_TYPES = {
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def export(db: Session, business_id: int, year: int, fmt: str) -> tuple[Dict[str, object], str]:
    """Dispatch export by format. Returns (result_dict, media_type)."""
    if fmt == "excel":
        result = export_to_excel(db, business_id, year)
    else:
        result = export_to_pdf(db, business_id, year)
    return result, _MEDIA_TYPES[fmt]