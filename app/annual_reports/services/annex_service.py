"""Service mixin for annex (schedule) data lines."""

from typing import Optional

from app.core.exceptions import NotFoundError
from app.annual_reports.models.annual_report_enums import AnnualReportSchedule
from app.annual_reports.repositories.annex_data_repository import AnnexDataRepository
from app.annual_reports.schemas.annual_report_annex import AnnexDataLineResponse
from .base import AnnualReportBaseService


class AnnualReportAnnexService(AnnualReportBaseService):
    """Mixin — requires self.db and self.repo (AnnualReportRepository)."""

    def _get_annex_repo(self) -> AnnexDataRepository:
        return AnnexDataRepository(self.db)  # type: ignore[attr-defined]

    def get_annex_lines(
        self, report_id: int, schedule: AnnualReportSchedule
    ) -> list[AnnexDataLineResponse]:
        self._get_or_raise(report_id)
        repo = self._get_annex_repo()
        rows = repo.list_by_report_and_schedule(report_id, schedule)
        return [AnnexDataLineResponse.model_validate(r) for r in rows]

    def add_annex_line(
        self,
        report_id: int,
        schedule: AnnualReportSchedule,
        data: dict,
        notes: Optional[str] = None,
    ) -> AnnexDataLineResponse:
        self._get_or_raise(report_id)
        repo = self._get_annex_repo()
        line_number = repo.next_line_number(report_id, schedule)
        row = repo.add_line(report_id, schedule, line_number, data, notes)
        return AnnexDataLineResponse.model_validate(row)

    def update_annex_line(
        self,
        report_id: int,
        line_id: int,
        data: dict,
        notes: Optional[str] = None,
    ) -> AnnexDataLineResponse:
        self._get_or_raise(report_id)
        repo = self._get_annex_repo()
        row = repo.update_line(line_id, data, notes)
        if not row:
            raise NotFoundError(f"שורת נספח {line_id} לא נמצאה", "ANNUAL_REPORT.LINE_NOT_FOUND")
        return AnnexDataLineResponse.model_validate(row)

    def delete_annex_line(self, report_id: int, line_id: int) -> None:
        self._get_or_raise(report_id)
        repo = self._get_annex_repo()
        if not repo.delete_line(line_id):
            raise NotFoundError(f"שורת נספח {line_id} לא נמצאה", "ANNUAL_REPORT.LINE_NOT_FOUND")


__all__ = ["AnnualReportAnnexService"]
