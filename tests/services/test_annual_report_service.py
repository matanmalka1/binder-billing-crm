"""
Tests for Annual Income Tax Report service.

Covers:
  - Form-to-client-type enforcement (1215/1301/6111)
  - Duplicate prevention (one report per client per year)
  - Deadline calculation (standard Apr 30, extended Jan 31)
  - Schedule auto-generation from income flags
  - Valid and invalid status transitions
  - Schedule completion tracking
  - Season summary aggregation
  - Overdue detection
  - Status history audit trail
"""

from datetime import datetime
from unittest.mock import MagicMock


# ─── Inline enums (no SQLAlchemy) ─────────────────────────────────────────────

from enum import Enum as PyEnum

class ClientTypeForReport(str, PyEnum):
    INDIVIDUAL    = "individual"
    SELF_EMPLOYED = "self_employed"
    CORPORATION   = "corporation"
    PARTNERSHIP   = "partnership"

class AnnualReportForm(str, PyEnum):
    FORM_1301 = "1301"
    FORM_1215 = "1215"
    FORM_6111 = "6111"

class AnnualReportStatus(str, PyEnum):
    NOT_STARTED       = "not_started"
    COLLECTING_DOCS   = "collecting_docs"
    DOCS_COMPLETE     = "docs_complete"
    IN_PREPARATION    = "in_preparation"
    PENDING_CLIENT    = "pending_client"
    SUBMITTED         = "submitted"
    ACCEPTED          = "accepted"
    ASSESSMENT_ISSUED = "assessment_issued"
    OBJECTION_FILED   = "objection_filed"
    CLOSED            = "closed"

class AnnualReportSchedule(str, PyEnum):
    SCHEDULE_B      = "schedule_b"
    SCHEDULE_BET    = "schedule_bet"
    SCHEDULE_GIMMEL = "schedule_gimmel"
    SCHEDULE_DALET  = "schedule_dalet"
    SCHEDULE_HEH    = "schedule_heh"

class DeadlineType(str, PyEnum):
    STANDARD = "standard"
    EXTENDED = "extended"
    CUSTOM   = "custom"


# ─── Constants (copy from service) ───────────────────────────────────────────

FORM_MAP = {
    ClientTypeForReport.INDIVIDUAL:    AnnualReportForm.FORM_1301,
    ClientTypeForReport.SELF_EMPLOYED: AnnualReportForm.FORM_1215,
    ClientTypeForReport.PARTNERSHIP:   AnnualReportForm.FORM_1215,
    ClientTypeForReport.CORPORATION:   AnnualReportForm.FORM_6111,
}

VALID_TRANSITIONS = {
    AnnualReportStatus.NOT_STARTED:      {AnnualReportStatus.COLLECTING_DOCS},
    AnnualReportStatus.COLLECTING_DOCS:  {AnnualReportStatus.DOCS_COMPLETE, AnnualReportStatus.NOT_STARTED},
    AnnualReportStatus.DOCS_COMPLETE:    {AnnualReportStatus.IN_PREPARATION, AnnualReportStatus.COLLECTING_DOCS},
    AnnualReportStatus.IN_PREPARATION:   {AnnualReportStatus.PENDING_CLIENT, AnnualReportStatus.DOCS_COMPLETE},
    AnnualReportStatus.PENDING_CLIENT:   {AnnualReportStatus.IN_PREPARATION, AnnualReportStatus.SUBMITTED},
    AnnualReportStatus.SUBMITTED:        {AnnualReportStatus.ACCEPTED, AnnualReportStatus.ASSESSMENT_ISSUED},
    AnnualReportStatus.ACCEPTED:         {AnnualReportStatus.CLOSED},
    AnnualReportStatus.ASSESSMENT_ISSUED:{AnnualReportStatus.OBJECTION_FILED, AnnualReportStatus.CLOSED},
    AnnualReportStatus.OBJECTION_FILED:  {AnnualReportStatus.CLOSED},
    AnnualReportStatus.CLOSED:           set(),
}

SCHEDULE_FLAGS = [
    ("has_rental_income",  AnnualReportSchedule.SCHEDULE_B),
    ("has_capital_gains",  AnnualReportSchedule.SCHEDULE_BET),
    ("has_foreign_income", AnnualReportSchedule.SCHEDULE_GIMMEL),
    ("has_depreciation",   AnnualReportSchedule.SCHEDULE_DALET),
    ("has_exempt_rental",  AnnualReportSchedule.SCHEDULE_HEH),
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

from datetime import timezone
def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _standard_deadline(tax_year):
    return datetime(tax_year + 1, 4, 30, 23, 59, 59)

def _extended_deadline(tax_year):
    return datetime(tax_year + 2, 1, 31, 23, 59, 59)


# ─── In-memory service (no DB) ───────────────────────────────────────────────

class _InMemoryRepo:
    def __init__(self):
        self._reports = {}
        self._schedules = {}   # report_id → list
        self._history = {}     # report_id → list
        self._next_id = 1
        self._sched_next = 1

    def create(self, **kwargs):
        r = MagicMock()
        r.id = self._next_id; self._next_id += 1
        r.status = AnnualReportStatus.NOT_STARTED
        for k, v in kwargs.items(): setattr(r, k, v)
        self._reports[r.id] = r
        self._schedules[r.id] = []
        self._history[r.id] = []
        return r

    def get_by_id(self, rid): return self._reports.get(rid)

    def get_by_client_year(self, client_id, tax_year):
        return next((r for r in self._reports.values()
                     if r.client_id == client_id and r.tax_year == tax_year), None)

    def list_by_client(self, client_id):
        return sorted([r for r in self._reports.values() if r.client_id == client_id],
                      key=lambda r: r.tax_year, reverse=True)

    def list_by_tax_year(self, tax_year, page=1, page_size=50):
        return [r for r in self._reports.values() if r.tax_year == tax_year]

    def count_by_tax_year(self, tax_year):
        return len(self.list_by_tax_year(tax_year))

    def list_overdue(self, tax_year=None):
        open_statuses = {
            AnnualReportStatus.NOT_STARTED, AnnualReportStatus.COLLECTING_DOCS,
            AnnualReportStatus.DOCS_COMPLETE, AnnualReportStatus.IN_PREPARATION,
            AnnualReportStatus.PENDING_CLIENT,
        }
        now = utcnow()
        results = [r for r in self._reports.values()
                   if r.status in open_statuses
                   and getattr(r, 'filing_deadline', None) is not None
                   and r.filing_deadline < now]
        if tax_year:
            results = [r for r in results if r.tax_year == tax_year]
        return results

    def update(self, rid, **fields):
        r = self._reports.get(rid)
        if not r: return None
        for k, v in fields.items(): setattr(r, k, v)
        return r

    def add_schedule(self, annual_report_id, schedule, is_required=True, notes=None):
        s = MagicMock()
        s.id = self._sched_next; self._sched_next += 1
        s.annual_report_id = annual_report_id
        s.schedule = schedule
        s.is_required = is_required
        s.is_complete = False
        s.notes = notes
        s.completed_at = None
        self._schedules.setdefault(annual_report_id, []).append(s)
        return s

    def get_schedules(self, rid): return self._schedules.get(rid, [])

    def mark_schedule_complete(self, rid, schedule):
        for s in self._schedules.get(rid, []):
            if s.schedule == schedule:
                s.is_complete = True
                s.completed_at = utcnow()
                return s
        return None

    def schedules_complete(self, rid):
        return all(s.is_complete for s in self._schedules.get(rid, []) if s.is_required)

    def append_status_history(self, annual_report_id, from_status, to_status,
                               changed_by, changed_by_name, note=None):
        h = MagicMock()
        h.from_status = from_status; h.to_status = to_status
        h.changed_by = changed_by; h.changed_by_name = changed_by_name
        h.note = note; h.occurred_at = utcnow()
        self._history.setdefault(annual_report_id, []).append(h)
        return h

    def get_status_history(self, rid): return self._history.get(rid, [])

    def get_season_summary(self, tax_year):
        reports = self.list_by_tax_year(tax_year)
        summary = {s.value: 0 for s in AnnualReportStatus}
        for r in reports: summary[r.status.value] += 1
        summary["total"] = len(reports)
        return summary


class AnnualReportService:
    def __init__(self):
        self.repo = _InMemoryRepo()
        self.client_repo = MagicMock()
        self.client_repo.get_by_id.return_value = MagicMock(id=1)

    def create_report(self, client_id, tax_year, client_type, created_by, created_by_name,
                      deadline_type="standard", assigned_to=None, notes=None,
                      has_rental_income=False, has_capital_gains=False,
                      has_foreign_income=False, has_depreciation=False, has_exempt_rental=False):
        client = self.client_repo.get_by_id(client_id)
        if not client: raise ValueError(f"Client {client_id} not found")
        try: ct = ClientTypeForReport(client_type)
        except ValueError: raise ValueError(f"Invalid client_type '{client_type}'")
        try: dt = DeadlineType(deadline_type)
        except ValueError: raise ValueError(f"Invalid deadline_type '{deadline_type}'")

        existing = self.repo.get_by_client_year(client_id, tax_year)
        if existing: raise ValueError(f"Report already exists for client {client_id} year {tax_year}")

        form_type = FORM_MAP[ct]
        filing_deadline = (_standard_deadline(tax_year) if dt == DeadlineType.STANDARD
                           else _extended_deadline(tax_year) if dt == DeadlineType.EXTENDED
                           else None)

        report = self.repo.create(
            client_id=client_id, tax_year=tax_year, client_type=ct,
            form_type=form_type, created_by=created_by, assigned_to=assigned_to,
            status=AnnualReportStatus.NOT_STARTED, deadline_type=dt,
            filing_deadline=filing_deadline, notes=notes,
            has_rental_income=has_rental_income, has_capital_gains=has_capital_gains,
            has_foreign_income=has_foreign_income, has_depreciation=has_depreciation,
            has_exempt_rental=has_exempt_rental,
        )

        for flag_attr, schedule in SCHEDULE_FLAGS:
            if locals().get(flag_attr) or getattr(report, flag_attr, False):
                self.repo.add_schedule(report.id, schedule, is_required=True)

        # Re-check flags from kwargs since they're local
        flag_map = {
            "has_rental_income": has_rental_income, "has_capital_gains": has_capital_gains,
            "has_foreign_income": has_foreign_income, "has_depreciation": has_depreciation,
            "has_exempt_rental": has_exempt_rental,
        }
        # Clear and re-generate (simple approach)
        self.repo._schedules[report.id] = []
        for flag_attr, schedule in SCHEDULE_FLAGS:
            if flag_map.get(flag_attr, False):
                self.repo.add_schedule(report.id, schedule, is_required=True)

        self.repo.append_status_history(report.id, None, AnnualReportStatus.NOT_STARTED, created_by, created_by_name)
        return report

    def transition_status(self, report_id, new_status, changed_by, changed_by_name, note=None, **kwargs):
        report = self._get_or_raise(report_id)
        try: ns = AnnualReportStatus(new_status)
        except ValueError: raise ValueError(f"Invalid status '{new_status}'")
        if ns not in VALID_TRANSITIONS.get(report.status, set()):
            allowed = [s.value for s in VALID_TRANSITIONS.get(report.status, set())]
            raise ValueError(f"Cannot transition from '{report.status.value}' to '{ns.value}'. Allowed: {allowed}")
        old = report.status
        update = {"status": ns}
        if ns == AnnualReportStatus.SUBMITTED:
            update["submitted_at"] = utcnow()
            if kwargs.get("ita_reference"): update["ita_reference"] = kwargs["ita_reference"]
        report = self.repo.update(report_id, **update)
        self.repo.append_status_history(report_id, old, ns, changed_by, changed_by_name, note)
        return report

    def get_report(self, rid): return self.repo.get_by_id(rid)
    def get_client_reports(self, cid): return self.repo.list_by_client(cid)
    def get_season_summary(self, year): return self.repo.get_season_summary(year)
    def get_overdue(self, tax_year=None): return self.repo.list_overdue(tax_year)
    def get_schedules(self, rid):
        self._get_or_raise(rid); return self.repo.get_schedules(rid)
    def complete_schedule(self, rid, schedule):
        self._get_or_raise(rid)
        try: s = AnnualReportSchedule(schedule)
        except ValueError: raise ValueError(f"Invalid schedule '{schedule}'")
        entry = self.repo.mark_schedule_complete(rid, s)
        if not entry: raise ValueError(f"Schedule not found")
        return entry
    def schedules_complete(self, rid): return self.repo.schedules_complete(rid)
    def get_status_history(self, rid):
        self._get_or_raise(rid); return self.repo.get_status_history(rid)
    def _get_or_raise(self, rid):
        r = self.repo.get_by_id(rid)
        if not r: raise ValueError(f"Report {rid} not found")
        return r


# ─── Tests ────────────────────────────────────────────────────────────────────

passed = failed = 0

def run(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  ✓ {name}")
        passed += 1
    except Exception as e:
        import traceback
        print(f"  ✗ {name}: {e}")
        failed += 1


# ── Form mapping ──────────────────────────────────────────────────────────────
print("\n=== FORM-TO-CLIENT-TYPE MAPPING ===")

def t_individual_gets_1301():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor")
    assert r.form_type == AnnualReportForm.FORM_1301, f"Got {r.form_type}"
run("individual → form 1301", t_individual_gets_1301)

def t_self_employed_gets_1215():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "self_employed", 1, "Advisor")
    assert r.form_type == AnnualReportForm.FORM_1215
run("self_employed → form 1215", t_self_employed_gets_1215)

def t_partnership_gets_1215():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "partnership", 1, "Advisor")
    assert r.form_type == AnnualReportForm.FORM_1215
run("partnership → form 1215", t_partnership_gets_1215)

def t_corporation_gets_6111():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "corporation", 1, "Advisor")
    assert r.form_type == AnnualReportForm.FORM_6111
run("corporation → form 6111", t_corporation_gets_6111)

def t_invalid_client_type():
    s = AnnualReportService()
    try: s.create_report(1, 2023, "alien", 1, "Advisor"); assert False
    except ValueError as e: assert "Invalid client_type" in str(e)
run("invalid client_type raises", t_invalid_client_type)


# ── Deadline calculation ──────────────────────────────────────────────────────
print("\n=== DEADLINE CALCULATION ===")

def t_standard_deadline():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor", deadline_type="standard")
    assert r.filing_deadline == datetime(2024, 4, 30, 23, 59, 59), f"Got {r.filing_deadline}"
run("standard deadline = April 30 following year", t_standard_deadline)

def t_extended_deadline():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor", deadline_type="extended")
    assert r.filing_deadline == datetime(2025, 1, 31, 23, 59, 59), f"Got {r.filing_deadline}"
run("extended deadline = Jan 31 two years later (מייצגים)", t_extended_deadline)

def t_custom_deadline_none():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor", deadline_type="custom")
    assert r.filing_deadline is None
run("custom deadline_type leaves filing_deadline None", t_custom_deadline_none)

def t_extended_is_later_than_standard():
    s = AnnualReportService()
    r_std = s.create_report(1, 2023, "individual", 1, "Advisor", deadline_type="standard")
    r_ext = s.create_report(2, 2023, "individual", 1, "Advisor", deadline_type="extended")
    assert r_ext.filing_deadline > r_std.filing_deadline
run("extended deadline > standard deadline", t_extended_is_later_than_standard)


# ── Duplicate prevention ──────────────────────────────────────────────────────
print("\n=== DUPLICATE PREVENTION ===")

def t_duplicate_same_client_year():
    s = AnnualReportService()
    s.create_report(1, 2023, "individual", 1, "Advisor")
    try: s.create_report(1, 2023, "individual", 1, "Advisor"); assert False
    except ValueError as e: assert "already exists" in str(e)
run("duplicate (client, year) raises", t_duplicate_same_client_year)

def t_different_year_ok():
    s = AnnualReportService()
    r1 = s.create_report(1, 2022, "individual", 1, "Advisor")
    r2 = s.create_report(1, 2023, "individual", 1, "Advisor")
    assert r1.id != r2.id
run("same client different years = OK", t_different_year_ok)

def t_different_client_same_year_ok():
    s = AnnualReportService()
    r1 = s.create_report(1, 2023, "individual", 1, "Advisor")
    r2 = s.create_report(2, 2023, "individual", 1, "Advisor")
    assert r1.id != r2.id
run("different clients same year = OK", t_different_client_same_year_ok)


# ── Schedule auto-generation ──────────────────────────────────────────────────
print("\n=== SCHEDULE AUTO-GENERATION ===")

def t_no_flags_no_schedules():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor")
    assert len(s.get_schedules(r.id)) == 0
run("no income flags → no schedules", t_no_flags_no_schedules)

def t_rental_income_creates_schedule_b():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor", has_rental_income=True)
    schedules = [sc.schedule for sc in s.get_schedules(r.id)]
    assert AnnualReportSchedule.SCHEDULE_B in schedules
run("has_rental_income → Schedule B created", t_rental_income_creates_schedule_b)

def t_capital_gains_creates_schedule_bet():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor", has_capital_gains=True)
    schedules = [sc.schedule for sc in s.get_schedules(r.id)]
    assert AnnualReportSchedule.SCHEDULE_BET in schedules
run("has_capital_gains → Schedule Bet created", t_capital_gains_creates_schedule_bet)

def t_multiple_flags_multiple_schedules():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor",
                        has_rental_income=True, has_capital_gains=True, has_foreign_income=True)
    schedules = [sc.schedule for sc in s.get_schedules(r.id)]
    assert AnnualReportSchedule.SCHEDULE_B in schedules
    assert AnnualReportSchedule.SCHEDULE_BET in schedules
    assert AnnualReportSchedule.SCHEDULE_GIMMEL in schedules
    assert len(schedules) == 3
run("3 flags → 3 schedules auto-created", t_multiple_flags_multiple_schedules)

def t_all_flags_all_schedules():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor",
                        has_rental_income=True, has_capital_gains=True,
                        has_foreign_income=True, has_depreciation=True, has_exempt_rental=True)
    assert len(s.get_schedules(r.id)) == 5
run("all 5 flags → all 5 schedules", t_all_flags_all_schedules)

def t_schedules_start_incomplete():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor", has_rental_income=True)
    schedules = s.get_schedules(r.id)
    assert all(not sc.is_complete for sc in schedules)
run("auto-generated schedules start incomplete", t_schedules_start_incomplete)

def t_complete_schedule():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor", has_rental_income=True)
    s.complete_schedule(r.id, "schedule_b")
    schedules = s.get_schedules(r.id)
    assert all(sc.is_complete for sc in schedules)
    assert s.schedules_complete(r.id)
run("completing schedule marks is_complete", t_complete_schedule)

def t_schedules_not_complete_until_all_done():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor",
                        has_rental_income=True, has_capital_gains=True)
    s.complete_schedule(r.id, "schedule_b")
    assert not s.schedules_complete(r.id)  # bet still pending
    s.complete_schedule(r.id, "schedule_bet")
    assert s.schedules_complete(r.id)
run("schedules_complete only true when all done", t_schedules_not_complete_until_all_done)


# ── Status transitions ────────────────────────────────────────────────────────
print("\n=== STATUS TRANSITIONS ===")

def _full_pipeline(s, client_id=1):
    r = s.create_report(client_id, 2023, "individual", 1, "Advisor")
    s.transition_status(r.id, "collecting_docs", 1, "Advisor")
    s.transition_status(r.id, "docs_complete", 1, "Advisor")
    s.transition_status(r.id, "in_preparation", 1, "Advisor")
    s.transition_status(r.id, "pending_client", 1, "Advisor")
    s.transition_status(r.id, "submitted", 1, "Advisor")
    s.transition_status(r.id, "accepted", 1, "Advisor")
    s.transition_status(r.id, "closed", 1, "Advisor")
    return r

def t_full_happy_path():
    s = AnnualReportService()
    r = _full_pipeline(s)
    final = s.get_report(r.id)
    assert final.status == AnnualReportStatus.CLOSED
run("full happy path: NOT_STARTED → CLOSED", t_full_happy_path)

def t_invalid_skip():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor")
    try: s.transition_status(r.id, "submitted", 1, "Advisor"); assert False
    except ValueError as e: assert "Cannot transition" in str(e)
run("skipping steps raises ValueError", t_invalid_skip)

def t_cannot_reopen_closed():
    s = AnnualReportService()
    r = _full_pipeline(s)
    try: s.transition_status(r.id, "collecting_docs", 1, "Advisor"); assert False
    except ValueError: pass
run("cannot transition out of CLOSED", t_cannot_reopen_closed)

def t_assessment_path():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor")
    s.transition_status(r.id, "collecting_docs", 1, "A")
    s.transition_status(r.id, "docs_complete", 1, "A")
    s.transition_status(r.id, "in_preparation", 1, "A")
    s.transition_status(r.id, "pending_client", 1, "A")
    s.transition_status(r.id, "submitted", 1, "A")
    s.transition_status(r.id, "assessment_issued", 1, "A", assessment_amount=50000)
    s.transition_status(r.id, "objection_filed", 1, "A")
    s.transition_status(r.id, "closed", 1, "A")
    final = s.get_report(r.id)
    assert final.status == AnnualReportStatus.CLOSED
run("assessment → objection → closed path", t_assessment_path)

def t_backward_transition_allowed():
    """collecting_docs → not_started is explicitly allowed (re-open)."""
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor")
    s.transition_status(r.id, "collecting_docs", 1, "Advisor")
    s.transition_status(r.id, "not_started", 1, "Advisor")
    assert s.get_report(r.id).status == AnnualReportStatus.NOT_STARTED
run("allowed backward transition (collecting → not_started)", t_backward_transition_allowed)


# ── Status history ────────────────────────────────────────────────────────────
print("\n=== STATUS HISTORY ===")

def t_history_recorded():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor")
    s.transition_status(r.id, "collecting_docs", 1, "Advisor", note="Started collection")
    history = s.get_status_history(r.id)
    assert len(history) == 2  # created + transition
    assert history[-1].to_status == AnnualReportStatus.COLLECTING_DOCS
    assert history[-1].note == "Started collection"
run("status history records transitions", t_history_recorded)

def t_history_first_entry_from_none():
    s = AnnualReportService()
    r = s.create_report(1, 2023, "individual", 1, "Advisor")
    history = s.get_status_history(r.id)
    assert history[0].from_status is None
    assert history[0].to_status == AnnualReportStatus.NOT_STARTED
run("first history entry has from_status=None", t_history_first_entry_from_none)


# ── Season summary ────────────────────────────────────────────────────────────
print("\n=== SEASON SUMMARY ===")

def t_season_summary_counts():
    s = AnnualReportService()
    # 3 clients, 2023
    s.create_report(1, 2023, "individual", 1, "A")
    r2 = s.create_report(2, 2023, "corporation", 1, "A")
    r3 = s.create_report(3, 2023, "self_employed", 1, "A")
    # Advance r2 to submitted
    s.transition_status(r2.id, "collecting_docs", 1, "A")
    s.transition_status(r2.id, "docs_complete", 1, "A")
    s.transition_status(r2.id, "in_preparation", 1, "A")
    s.transition_status(r2.id, "pending_client", 1, "A")
    s.transition_status(r2.id, "submitted", 1, "A")

    summary = s.get_season_summary(2023)
    assert summary["total"] == 3
    assert summary["submitted"] == 1
    assert summary["not_started"] == 2
run("season summary counts by status", t_season_summary_counts)

def t_season_summary_different_years_isolated():
    s = AnnualReportService()
    s.create_report(1, 2022, "individual", 1, "A")
    s.create_report(1, 2023, "individual", 1, "A")
    assert s.get_season_summary(2022)["total"] == 1
    assert s.get_season_summary(2023)["total"] == 1
run("season summaries are isolated by year", t_season_summary_different_years_isolated)


# ── Overdue detection ─────────────────────────────────────────────────────────
print("\n=== OVERDUE DETECTION ===")

def t_past_deadline_is_overdue():
    s = AnnualReportService()
    # tax year 2020 → standard deadline was April 30 2021 (in the past)
    r = s.create_report(1, 2020, "individual", 1, "A", deadline_type="standard")
    overdue = s.get_overdue()
    assert any(o.id == r.id for o in overdue)
run("report past standard deadline appears in overdue list", t_past_deadline_is_overdue)

def t_submitted_not_overdue():
    s = AnnualReportService()
    r = s.create_report(1, 2020, "individual", 1, "A")
    # Advance to submitted
    for st in ["collecting_docs", "docs_complete", "in_preparation", "pending_client", "submitted"]:
        s.transition_status(r.id, st, 1, "A")
    overdue = s.get_overdue()
    assert not any(o.id == r.id for o in overdue)
run("submitted report not in overdue list", t_submitted_not_overdue)

def t_future_deadline_not_overdue():
    s = AnnualReportService()
    # tax year 2099 → deadline is 2100, safely in the future
    r = s.create_report(1, 2099, "individual", 1, "A", deadline_type="standard")
    overdue = s.get_overdue(tax_year=2099)
    assert not any(o.id == r.id for o in overdue)
run("future deadline not in overdue list", t_future_deadline_not_overdue)


# ─── Results ─────────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"Results: {passed} passed, {failed} failed")
import sys
if failed: sys.exit(1)