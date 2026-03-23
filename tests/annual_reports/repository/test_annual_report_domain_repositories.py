from datetime import date
from decimal import Decimal

from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportSchedule,
    AnnualReportStatus,
    ClientTypeForReport,
    DeadlineType,
)
from app.annual_reports.models.annual_report_expense_line import ExpenseCategoryType
from app.annual_reports.models.annual_report_income_line import IncomeSourceType
from app.annual_reports.repositories.annex_data_repository import AnnexDataRepository
from app.annual_reports.repositories.detail.repository import AnnualReportDetailRepository
from app.annual_reports.repositories.expense_repository import AnnualReportExpenseRepository
from app.annual_reports.repositories.income_repository import AnnualReportIncomeRepository
from app.annual_reports.repositories.report_repository import AnnualReportReportRepository
from app.clients.models import Client
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def _user(test_db) -> User:
    user = User(
        full_name="Annual Domain Repo User",
        email="annual.domain.repo@example.com",
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
        full_name="Annual Domain Repo Client",
        id_number="ADR001",

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


def test_detail_annex_income_and_expense_repository_methods(test_db):
    user = _user(test_db)
    report_id = _report_id(test_db, user.id)

    detail_repo = AnnualReportDetailRepository(test_db)
    annex_repo = AnnexDataRepository(test_db)
    income_repo = AnnualReportIncomeRepository(test_db)
    expense_repo = AnnualReportExpenseRepository(test_db)

    assert detail_repo.get_by_report_id(report_id) is None
    created_detail = detail_repo.upsert(
        report_id,
        internal_notes="initial",
    )
    fetched_detail = detail_repo.get_by_report_id(report_id)
    assert fetched_detail.id == created_detail.id
    updated_detail = detail_repo.upsert(report_id, internal_notes="updated")
    assert updated_detail.id == created_detail.id
    assert updated_detail.internal_notes == "updated"

    assert annex_repo.next_line_number(report_id, AnnualReportSchedule.SCHEDULE_B) == 1
    line1 = annex_repo.add_line(
        report_id,
        AnnualReportSchedule.SCHEDULE_B,
        line_number=1,
        data={"gross": 1000},
        notes="line1",
    )
    line2 = annex_repo.add_line(
        report_id,
        AnnualReportSchedule.SCHEDULE_B,
        line_number=2,
        data={"gross": 2000},
        notes="line2",
    )

    lines = annex_repo.list_by_report_and_schedule(report_id, AnnualReportSchedule.SCHEDULE_B)
    assert [line.id for line in lines] == [line1.id, line2.id]
    assert annex_repo.count_by_report_and_schedule(report_id, AnnualReportSchedule.SCHEDULE_B) == 2
    assert annex_repo.next_line_number(report_id, AnnualReportSchedule.SCHEDULE_B) == 3

    updated_line = annex_repo.update_line(line1.id, data={"gross": 1500}, notes="revised")
    assert updated_line.data == {"gross": 1500}
    assert updated_line.notes == "revised"
    assert annex_repo.delete_line(line2.id) is True
    assert annex_repo.count_by_report_and_schedule(report_id, AnnualReportSchedule.SCHEDULE_B) == 1
    assert annex_repo.delete_line(999999) is False

    income_repo.add(
        annual_report_id=report_id,
        source_type=IncomeSourceType.SALARY,
        amount=Decimal("2000.00"),
    )
    income_repo.add(
        annual_report_id=report_id,
        source_type=IncomeSourceType.BUSINESS,
        amount=Decimal("500.00"),
    )
    income_lines = income_repo.list_by_report(report_id)
    assert [line.source_type for line in income_lines] == [
        IncomeSourceType.BUSINESS,
        IncomeSourceType.SALARY,
    ]
    assert income_repo.total_income(report_id) == Decimal("2500.0")

    expense_repo.add(
        annual_report_id=report_id,
        category=ExpenseCategoryType.MARKETING,
        amount=Decimal("300.00"),
    )
    expense_repo.add(
        annual_report_id=report_id,
        category=ExpenseCategoryType.OTHER,
        amount=Decimal("100.00"),
    )
    expense_lines = expense_repo.list_by_report(report_id)
    assert [line.category for line in expense_lines] == [
        ExpenseCategoryType.MARKETING,
        ExpenseCategoryType.OTHER,
    ]
    assert expense_repo.total_expenses(report_id) == Decimal("400.0")
