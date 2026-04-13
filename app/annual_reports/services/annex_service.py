"""Service mixin for annex (schedule) data lines."""

from typing import Optional

from app.core.exceptions import AppError, NotFoundError
from app.annual_reports.models.annual_report_enums import AnnualReportSchedule
from app.annual_reports.schemas.annual_report_annex import AnnexDataLineResponse
from app.annual_reports.schemas.annex_schemas import SCHEDULE_VALIDATORS
from .base import AnnualReportBaseService
from .messages import ANNEX_LINE_NOT_FOUND, ANNEX_VALIDATION_ERROR


class AnnualReportAnnexService(AnnualReportBaseService):
    """Mixin — requires self.annex_repo (AnnexDataRepository) wired in facade __init__."""

    def _validate_annex_data(self, schedule: AnnualReportSchedule, data: dict) -> dict:
        """Validate annex data dict against the per-schedule Pydantic schema.

        Returns the validated (and coerced) data dict.
        If no schema is defined for the schedule the dict passes through unchanged.
        """
        validator_cls = SCHEDULE_VALIDATORS.get(schedule.value)
        if validator_cls is None:
            return data
        try:
            validated = validator_cls(**data)
            # Convert Decimal values to float so the dict is JSON-serializable
            # before being stored in the JSON column (SQLite/PostgreSQL JSON type).
            raw = validated.model_dump(exclude_none=True)
            return {
                k: float(v) if hasattr(v, "__round__") and not isinstance(v, (int, float, bool)) else v
                for k, v in raw.items()
            }
        except Exception as exc:
            raise AppError(
                ANNEX_VALIDATION_ERROR.format(error=exc),
                "ANNUAL_REPORT.ANNEX_VALIDATION_ERROR",
            ) from exc

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
        data = self._validate_annex_data(schedule, data)
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
        existing = self.annex_repo.get_by_id(line_id)  # type: ignore[attr-defined]
        if not existing:
            raise NotFoundError(ANNEX_LINE_NOT_FOUND.format(line_id=line_id), "ANNUAL_REPORT.LINE_NOT_FOUND")
        data = self._validate_annex_data(existing.schedule, data)
        row = self.annex_repo.update_line(line_id, data, notes)  # type: ignore[attr-defined]
        if not row:
            raise NotFoundError(ANNEX_LINE_NOT_FOUND.format(line_id=line_id), "ANNUAL_REPORT.LINE_NOT_FOUND")
        return AnnexDataLineResponse.model_validate(row)

    def delete_annex_line(self, report_id: int, line_id: int) -> None:
        self._get_or_raise(report_id)
        if not self.annex_repo.delete_line(line_id):  # type: ignore[attr-defined]
            raise NotFoundError(ANNEX_LINE_NOT_FOUND.format(line_id=line_id), "ANNUAL_REPORT.LINE_NOT_FOUND")


__all__ = ["AnnualReportAnnexService"]
