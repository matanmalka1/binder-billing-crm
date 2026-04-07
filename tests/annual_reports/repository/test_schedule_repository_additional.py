from datetime import date

from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportSchedule,
    AnnualReportStatus,
    ClientTypeForReport,
    DeadlineType,
)
from app.annual_reports.repositories.report_repository import AnnualReportReportRepository
from app.annual_reports.repositories.schedule_repository import AnnualReportScheduleRepository
from app.clients.models.client import Client
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def _user(test_db) -> User:
    user = User(
        full_name="Schedule Repo User",
        email="schedule.repo@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _report_id(test_db, user_id: int) -> int:
    client = Client(
        full_name="Schedule Repo Client",
        id_number="SCHEDULE001",

    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    report = AnnualReportReportRepository(test_db).create(
        business_id=client.id,
        created_by=user_id,
        tax_year=2026,
        client_type=ClientTypeForReport.CORPORATION,
        form_type=AnnualReportForm.FORM_6111,
        status=AnnualReportStatus.NOT_STARTED,
        deadline_type=DeadlineType.STANDARD,
    )
    return report.id


def test_schedules_complete_handles_required_and_optional(test_db):
    user = _user(test_db)
    report_id = _report_id(test_db, user.id)
    repo = AnnualReportScheduleRepository(test_db)

    required_entry = repo.add_schedule(
        annual_report_id=report_id,
        schedule=AnnualReportSchedule.SCHEDULE_B,
        is_required=True,
    )
    repo.add_schedule(
        annual_report_id=report_id,
        schedule=AnnualReportSchedule.SCHEDULE_GIMMEL,
        is_required=False,
    )

    assert repo.schedules_complete(report_id) is False

    marked = repo.mark_schedule_complete(report_id, AnnualReportSchedule.SCHEDULE_B)
    assert marked is not None
    assert marked.id == required_entry.id

    assert repo.schedules_complete(report_id) is True


def test_schedules_complete_returns_true_when_no_required_entries(test_db):
    user = _user(test_db)
    report_id = _report_id(test_db, user.id)
    repo = AnnualReportScheduleRepository(test_db)

    repo.add_schedule(
        annual_report_id=report_id,
        schedule=AnnualReportSchedule.SCHEDULE_B,
        is_required=False,
    )

    assert repo.schedules_complete(report_id) is True
