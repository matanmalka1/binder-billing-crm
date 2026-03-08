from unittest.mock import MagicMock

from .annual_report_enums import (
    AnnualReportForm,
    AnnualReportSchedule,
    AnnualReportStatus,
    ClientTypeForReport,
    DeadlineType,
    FORM_MAP,
    SCHEDULE_FLAGS,
    VALID_TRANSITIONS,
    extended_deadline,
    standard_deadline,
    utcnow,
)
from .annual_report_repo import InMemoryRepo


class AnnualReportService:
    def __init__(self):
        self.repo = InMemoryRepo()
        self.client_repo = MagicMock()
        self.client_repo.get_by_id.return_value = MagicMock(id=1)

    def create_report(
        self,
        client_id,
        tax_year,
        client_type,
        created_by,
        created_by_name,
        deadline_type="standard",
        assigned_to=None,
        notes=None,
        has_rental_income=False,
        has_capital_gains=False,
        has_foreign_income=False,
        has_depreciation=False,
        has_exempt_rental=False,
    ):
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"הלקוח {client_id} לא נמצא")
        try:
            ct = ClientTypeForReport(client_type)
        except ValueError:
            raise ValueError(f"סוג לקוח '{client_type}' אינו חוקי")
        try:
            dt = DeadlineType(deadline_type)
        except ValueError:
            raise ValueError(f"סוג מועד אחרון '{deadline_type}' אינו חוקי")

        if self.repo.get_by_client_year(client_id, tax_year):
            raise ValueError(f"דוח כבר קיים עבור לקוח {client_id} לשנת {tax_year}")

        form_type = FORM_MAP[ct]
        filing_deadline = (
            standard_deadline(tax_year)
            if dt == DeadlineType.STANDARD
            else extended_deadline(tax_year)
            if dt == DeadlineType.EXTENDED
            else None
        )

        report = self.repo.create(
            client_id=client_id,
            tax_year=tax_year,
            client_type=ct,
            form_type=form_type,
            created_by=created_by,
            assigned_to=assigned_to,
            status=AnnualReportStatus.NOT_STARTED,
            deadline_type=dt,
            filing_deadline=filing_deadline,
            notes=notes,
            has_rental_income=has_rental_income,
            has_capital_gains=has_capital_gains,
            has_foreign_income=has_foreign_income,
            has_depreciation=has_depreciation,
            has_exempt_rental=has_exempt_rental,
        )

        for flag_attr, schedule in SCHEDULE_FLAGS:
            if getattr(report, flag_attr, False):
                self.repo.add_schedule(report.id, schedule, is_required=True)

        self.repo.append_status_history(report.id, None, AnnualReportStatus.NOT_STARTED, created_by, created_by_name)
        return report

    def transition_status(self, report_id, new_status, changed_by, changed_by_name, note=None, **kwargs):
        report = self._get_or_raise(report_id)
        try:
            ns = AnnualReportStatus(new_status)
        except ValueError:
            raise ValueError(f"סטטוס '{new_status}' אינו חוקי")
        if ns not in VALID_TRANSITIONS.get(report.status, set()):
            allowed = [s.value for s in VALID_TRANSITIONS.get(report.status, set())]
            raise ValueError(
                f"לא ניתן לעבור מסטטוס '{report.status.value}' ל'{ns.value}'. מותר: {allowed}"
            )
        previous_status = report.status
        update = {"status": ns}
        if ns == AnnualReportStatus.SUBMITTED:
            update["submitted_at"] = utcnow()
            if kwargs.get("ita_reference"):
                update["ita_reference"] = kwargs["ita_reference"]
        self.repo.update(report_id, **update)
        self.repo.append_status_history(report_id, previous_status, ns, changed_by, changed_by_name, note)
        return self.repo.get_by_id(report_id)

    def get_report(self, rid):
        return self.repo.get_by_id(rid)

    def get_client_reports(self, cid):
        return self.repo.list_by_client(cid)

    def get_season_summary(self, year):
        return self.repo.get_season_summary(year)

    def get_overdue(self, tax_year=None):
        return self.repo.list_overdue(tax_year)

    def get_schedules(self, rid):
        self._get_or_raise(rid)
        return self.repo.get_schedules(rid)

    def complete_schedule(self, rid, schedule):
        self._get_or_raise(rid)
        try:
            sched = AnnualReportSchedule(schedule)
        except ValueError:
            raise ValueError(f"לוח זמנים '{schedule}' אינו חוקי")
        entry = self.repo.mark_schedule_complete(rid, sched)
        if not entry:
            raise ValueError("לוח זמנים לא נמצא")
        return entry

    def schedules_complete(self, rid):
        return self.repo.schedules_complete(rid)

    def get_status_history(self, rid):
        self._get_or_raise(rid)
        return self.repo.get_status_history(rid)

    def _get_or_raise(self, rid):
        report = self.repo.get_by_id(rid)
        if not report:
            raise ValueError(f"הדוח {rid} לא נמצא")
        return report
