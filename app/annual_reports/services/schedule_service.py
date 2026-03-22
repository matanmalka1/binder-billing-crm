from typing import Optional

from app.core.exceptions import AppError, NotFoundError
from app.annual_reports .models import AnnualReport, AnnualReportSchedule
from .base import AnnualReportBaseService
from .constants import SCHEDULE_FLAGS


class AnnualReportScheduleService(AnnualReportBaseService):
    def add_schedule(self, report_id: int, schedule: str, notes: Optional[str] = None):
        self._get_or_raise(report_id)
        s = self._parse_schedule(schedule)
        return self.repo.add_schedule(report_id, s, notes=notes)

    def complete_schedule(self, report_id: int, schedule: str):
        self._get_or_raise(report_id)
        s = self._parse_schedule(schedule)
        entry = self.repo.mark_schedule_complete(report_id, s)
        if not entry:
            raise NotFoundError(
                f"נספח '{schedule}' לא נמצא בדוח {report_id}",
                "ANNUAL_REPORT.LINE_NOT_FOUND",
            )
        return entry

    def _parse_schedule(self, schedule: str) -> AnnualReportSchedule:
        try:
            return AnnualReportSchedule(schedule)
        except ValueError:
            raise AppError(
                f"נספח לא חוקי: '{schedule}'",
                "ANNUAL_REPORT.INVALID_TYPE",
            )

    def get_schedules(self, report_id: int):
        self._get_or_raise(report_id)
        return self.repo.get_schedules(report_id)

    def schedules_complete(self, report_id: int) -> bool:
        return self.repo.schedules_complete(report_id)

    # internal
    def _generate_schedules(self, report: AnnualReport) -> None:
        for flag_attr, schedule in SCHEDULE_FLAGS:
            if getattr(report, flag_attr, False):
                self.repo.add_schedule(
                    annual_report_id=report.id,
                    schedule=schedule,
                    is_required=True,
                )
