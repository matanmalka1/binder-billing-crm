from datetime import date
from decimal import Decimal

from app.annual_reports.models.annual_report_enums import (
    AnnualReportForm,
    AnnualReportStatus,
    ClientTypeForReport,
    DeadlineType,
)
from app.annual_reports.models.annual_report_expense_line import ExpenseCategoryType
from app.annual_reports.models.annual_report_income_line import IncomeSourceType
from app.annual_reports.repositories.expense_repository import AnnualReportExpenseRepository
from app.annual_reports.repositories.income_repository import AnnualReportIncomeRepository
from app.annual_reports.repositories.report_repository import AnnualReportReportRepository
from app.clients.models.client import Client


def _report_id(test_db) -> int:
    crm_client = Client(
        full_name="IncomeExpense Repo Client",
        id_number="AREPO001",

    )
    test_db.add(crm_client)
    test_db.commit()
    test_db.refresh(crm_client)

    report = AnnualReportReportRepository(test_db).create(
        business_id=crm_client.id,
        created_by=1,
        tax_year=2026,
        client_type=ClientTypeForReport.CORPORATION,
        form_type=AnnualReportForm.FORM_6111,
        status=AnnualReportStatus.NOT_STARTED,
        deadline_type=DeadlineType.STANDARD,
    )
    return report.id


def test_income_repo_get_update_delete_paths(test_db):
    report_id = _report_id(test_db)
    repo = AnnualReportIncomeRepository(test_db)

    line = repo.add(report_id, IncomeSourceType.SALARY, Decimal("100.00"), "salary")
    assert repo.get_by_id(line.id).id == line.id

    updated = repo.update(line.id, amount=Decimal("120.00"), description="updated")
    assert updated.amount == Decimal("120.00")
    assert updated.description == "updated"

    assert repo.update(999999, amount=Decimal("1.00")) is None
    assert repo.delete(line.id) is True
    assert repo.delete(999999) is False


def test_expense_repo_get_update_delete_paths(test_db):
    report_id = _report_id(test_db)
    repo = AnnualReportExpenseRepository(test_db)

    line = repo.add(report_id, ExpenseCategoryType.OTHER, Decimal("90.00"), "misc")
    assert repo.get_by_id(line.id).id == line.id

    updated = repo.update(line.id, amount=Decimal("95.00"), description="updated")
    assert updated.amount == Decimal("95.00")
    assert updated.description == "updated"

    assert repo.update(999999, amount=Decimal("1.00")) is None
    assert repo.delete(line.id) is True
    assert repo.delete(999999) is False
