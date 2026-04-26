from unittest.mock import MagicMock

from .test_annual_report_enums import (
    AnnualReportSchedule,
    AnnualReportStatus,
    utcnow,
)


class InMemoryRepo:
    def __init__(self):
        self._reports = {}
        self._schedules = {}
        self._history = {}
        self._next_id = 1
        self._sched_next = 1

    def create(self, **kwargs):
        report = MagicMock()
        report.id = self._next_id
        self._next_id += 1
        report.status = AnnualReportStatus.NOT_STARTED
        for key, value in kwargs.items():
            setattr(report, key, value)
        self._reports[report.id] = report
        self._schedules[report.id] = []
        self._history[report.id] = []
        return report

    def get_by_id(self, rid):
        return self._reports.get(rid)

    def get_by_client_year(self, client_record_id, tax_year):
        return next((r for r in self._reports.values() if r.client_record_id == client_record_id and r.tax_year == tax_year), None)

    def list_by_client(self, client_record_id):
        return sorted(
            [r for r in self._reports.values() if r.client_record_id == client_record_id],
            key=lambda r: r.tax_year,
            reverse=True,
        )

    def list_by_tax_year(self, tax_year, page=1, page_size=50):
        return [r for r in self._reports.values() if r.tax_year == tax_year]

    def count_by_tax_year(self, tax_year):
        return len(self.list_by_tax_year(tax_year))

    def list_overdue(self, tax_year=None):
        open_statuses = {
            AnnualReportStatus.NOT_STARTED,
            AnnualReportStatus.COLLECTING_DOCS,
            AnnualReportStatus.DOCS_COMPLETE,
            AnnualReportStatus.IN_PREPARATION,
            AnnualReportStatus.PENDING_CLIENT,
        }
        now = utcnow()
        results = [
            r
            for r in self._reports.values()
            if r.status in open_statuses and getattr(r, "filing_deadline", None) and r.filing_deadline < now
        ]
        if tax_year:
            results = [r for r in results if r.tax_year == tax_year]
        return results

    def update(self, rid, **fields):
        report = self._reports.get(rid)
        if not report:
            return None
        for key, value in fields.items():
            setattr(report, key, value)
        return report

    def add_schedule(self, annual_report_id, schedule, is_required=True, notes=None):
        schedule_obj = MagicMock()
        schedule_obj.id = self._sched_next
        self._sched_next += 1
        schedule_obj.annual_report_id = annual_report_id
        schedule_obj.schedule = schedule
        schedule_obj.is_required = is_required
        schedule_obj.is_complete = False
        schedule_obj.notes = notes
        schedule_obj.completed_at = None
        self._schedules.setdefault(annual_report_id, []).append(schedule_obj)
        return schedule_obj

    def get_schedules(self, rid):
        return self._schedules.get(rid, [])

    def mark_schedule_complete(self, rid, schedule):
        for sched in self._schedules.get(rid, []):
            if sched.schedule == schedule:
                sched.is_complete = True
                sched.completed_at = utcnow()
                return sched
        return None

    def schedules_complete(self, rid):
        return all(s.is_complete for s in self._schedules.get(rid, []) if s.is_required)

    def append_status_history(self, annual_report_id, from_status, to_status, changed_by, note=None):
        history = MagicMock()
        history.from_status = from_status
        history.to_status = to_status
        history.changed_by = changed_by
        history.note = note
        history.occurred_at = utcnow()
        self._history.setdefault(annual_report_id, []).append(history)
        return history

    def get_status_history(self, rid):
        return self._history.get(rid, [])

    def get_season_summary(self, tax_year):
        reports = self.list_by_tax_year(tax_year)
        summary = {status.value: 0 for status in AnnualReportStatus}
        for report in reports:
            summary[report.status.value] += 1
        summary["total"] = len(reports)
        return summary
