"""Summary builder for annual report financial lines."""

from app.annual_reports.schemas.annual_report_financials import (
    ExpenseLineResponse,
    FinancialSummaryResponse,
    IncomeLineResponse,
)


def build_financial_summary(service, report_id: int) -> FinancialSummaryResponse:
    service._get_report_or_raise(report_id)
    income_lines = service.income_repo.list_by_report(report_id)
    expense_lines = service.expense_repo.list_by_report(report_id)
    total_income = service.income_repo.total_income(report_id)
    gross_expenses = service.expense_repo.total_expenses(report_id)
    recognized_expenses = service.expense_repo.total_recognized_expenses(report_id)
    return FinancialSummaryResponse(
        annual_report_id=report_id,
        total_income=float(total_income),
        gross_expenses=float(gross_expenses),
        recognized_expenses=float(recognized_expenses),
        taxable_income=float(total_income - recognized_expenses),
        income_lines=[IncomeLineResponse.model_validate(line) for line in income_lines],
        expense_lines=[
            ExpenseLineResponse.model_validate(line) for line in expense_lines
        ],
    )
