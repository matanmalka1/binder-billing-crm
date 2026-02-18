from typing import Optional

from app.annual_reports .models import AnnualReport, AnnualReportSchedule
from .base import AnnualReportBaseService
from .constants import SCHEDULE_FLAGS


class AnnualReportScheduleService(AnnualReportBaseService):
    def add_schedule(self, report_id: int, schedule: str, notes: Optional[str] = None):
        self._get_or_raise(report_id)
        try:
            s = AnnualReportSchedule(schedule)
        except ValueError:
            valid = [e.value for e in AnnualReportSchedule]
            raise ValueError(f"Invalid schedule '{schedule}'. Valid: {valid}")
        return self.repo.add_schedule(report_id, s, notes=notes)

    def complete_schedule(self, report_id: int, schedule: str):
        self._get_or_raise(report_id)
        try:
            s = AnnualReportSchedule(schedule)
        except ValueError:
            raise ValueError(f"Invalid schedule '{schedule}'")
        entry = self.repo.mark_schedule_complete(report_id, s)
        if not entry:
            raise ValueError(f"Schedule '{schedule}' not found on report {report_id}")
        return entry

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
