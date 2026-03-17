"""Service mixin for annex (schedule) data lines."""

from typing import Optional

from app.core.exceptions import NotFoundError
from app.annual_reports.models.annual_report_enums import AnnualReportSchedule
from app.annual_reports.schemas.annual_report_annex import AnnexDataLineResponse
from .base import AnnualReportBaseService


class AnnualReportAnnexService(AnnualReportBaseService):
    """Mixin — requires self.annex_repo (AnnexDataRepository) wired in facade __init__."""

    def get_annex_lines(
        self, report_id: int, schedule: AnnualReportSchedule
    ) -> list[AnnexDataLineResponse]:
        self._get_or_raise(report_id)
        rows = self.annex_repo.list_by_report_and_schedule(report_id, schedule)  # type: ignore[attr-defined]
        return [AnnexDataLineResponse.model_validate(r) for r in rows]

    def add_annex_line(
        self,
        report_id: int,
        schedule: AnnualReportSchedule,
        data: dict,
        notes: Optional[str] = None,
    ) -> AnnexDataLineResponse:
        self._get_or_raise(report_id)
        line_number = self.annex_repo.next_line_number(report_id, schedule)  # type: ignore[attr-defined]
        row = self.annex_repo.add_line(report_id, schedule, line_number, data, notes)  # type: ignore[attr-defined]
        return AnnexDataLineResponse.model_validate(row)

    def update_annex_line(
        self,
        report_id: int,
        line_id: int,
        data: dict,
        notes: Optional[str] = None,
    ) -> AnnexDataLineResponse:
        self._get_or_raise(report_id)
        row = self.annex_repo.update_line(line_id, data, notes)  # type: ignore[attr-defined]
        if not row:
            raise NotFoundError(f"שורת נספח {line_id} לא נמצאה", "ANNUAL_REPORT.LINE_NOT_FOUND")
        return AnnexDataLineResponse.model_validate(row)

    def delete_annex_line(self, report_id: int, line_id: int) -> None:
        self._get_or_raise(report_id)
        if not self.annex_repo.delete_line(line_id):  # type: ignore[attr-defined]
            raise NotFoundError(f"שורת נספח {line_id} לא נמצאה", "ANNUAL_REPORT.LINE_NOT_FOUND")


__all__ = ["AnnualReportAnnexService"]
