"""CRUD and summary operations for annual report financial lines."""

from decimal import Decimal
from typing import Optional

from app.core.exceptions import AppError, NotFoundError
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.services.business_guards import assert_business_not_closed
from app.annual_reports.models.annual_report_expense_line import ExpenseCategoryType
from app.annual_reports.models.annual_report_income_line import IncomeSourceType
from app.annual_reports.schemas.annual_report_financials import (
    ExpenseLineResponse,
    FinancialSummaryResponse,
    IncomeLineResponse,
)


class FinancialCrudMixin:
    def add_income(
        self,
        report_id: int,
        source_type: str,
        amount: Decimal,
        description: Optional[str] = None,
    ) -> IncomeLineResponse:
        report = self._get_report_or_raise(report_id)
        business = BusinessRepository(self.db).get_by_id(report.business_id)
        if business:
            assert_business_not_closed(business)
        valid_sources = {e.value for e in IncomeSourceType}
        if source_type not in valid_sources:
            raise AppError(
                f"סוג הכנסה לא חוקי '{source_type}'. חוקיים: {sorted(valid_sources)}",
                "ANNUAL_REPORT.INVALID_TYPE",
            )
        line = self.income_repo.add(report_id, IncomeSourceType(source_type), amount, description)
        return IncomeLineResponse.model_validate(line)

    def update_income(self, report_id: int, line_id: int, **fields) -> IncomeLineResponse:
        self._get_report_or_raise(report_id)
        if "source_type" in fields and fields["source_type"] is not None:
            valid_sources = {e.value for e in IncomeSourceType}
            if fields["source_type"] not in valid_sources:
                raise AppError(f"סוג הכנסה לא חוקי. חוקיים: {sorted(valid_sources)}", "ANNUAL_REPORT.INVALID_TYPE")
            fields["source_type"] = IncomeSourceType(fields["source_type"])
        line = self.income_repo.update(line_id, **{k: v for k, v in fields.items() if v is not None})
        if not line:
            raise NotFoundError(f"שורת הכנסה {line_id} לא נמצאה", "ANNUAL_REPORT.LINE_NOT_FOUND")
        return IncomeLineResponse.model_validate(line)

    def delete_income(self, report_id: int, line_id: int) -> None:
        self._get_report_or_raise(report_id)
        if not self.income_repo.delete(line_id):
            raise NotFoundError(f"שורת הכנסה {line_id} לא נמצאה", "ANNUAL_REPORT.LINE_NOT_FOUND")

    def add_expense(
        self,
        report_id: int,
        category: str,
        amount: Decimal,
        description: Optional[str] = None,
        recognition_rate: Optional[Decimal] = None,
        supporting_document_ref: Optional[str] = None,
        supporting_document_id: Optional[int] = None,
    ) -> ExpenseLineResponse:
        report = self._get_report_or_raise(report_id)
        business = BusinessRepository(self.db).get_by_id(report.business_id)
        if business:
            assert_business_not_closed(business)
        valid_categories = {e.value for e in ExpenseCategoryType}
        if category not in valid_categories:
            raise AppError(
                f"קטגוריית הוצאה לא חוקית '{category}'. חוקיות: {sorted(valid_categories)}",
                "ANNUAL_REPORT.INVALID_TYPE",
            )
        line = self.expense_repo.add(
            report_id,
            ExpenseCategoryType(category),
            amount,
            description,
            recognition_rate,
            supporting_document_ref,
            supporting_document_id,
        )
        return ExpenseLineResponse.model_validate(line)

    def update_expense(self, report_id: int, line_id: int, **fields) -> ExpenseLineResponse:
        self._get_report_or_raise(report_id)
        if "category" in fields and fields["category"] is not None:
            valid_categories = {e.value for e in ExpenseCategoryType}
            if fields["category"] not in valid_categories:
                raise AppError(f"קטגוריית הוצאה לא חוקית. חוקיות: {sorted(valid_categories)}", "ANNUAL_REPORT.INVALID_TYPE")
            fields["category"] = ExpenseCategoryType(fields["category"])
        line = self.expense_repo.update(line_id, **{k: v for k, v in fields.items() if v is not None})
        if not line:
            raise NotFoundError(f"שורת הוצאה {line_id} לא נמצאה", "ANNUAL_REPORT.LINE_NOT_FOUND")
        return ExpenseLineResponse.model_validate(line)

    def delete_expense(self, report_id: int, line_id: int) -> None:
        self._get_report_or_raise(report_id)
        if not self.expense_repo.delete(line_id):
            raise NotFoundError(f"שורת הוצאה {line_id} לא נמצאה", "ANNUAL_REPORT.LINE_NOT_FOUND")

    def get_financial_summary(self, report_id: int) -> FinancialSummaryResponse:
        self._get_report_or_raise(report_id)
        income_lines = self.income_repo.list_by_report(report_id)
        expense_lines = self.expense_repo.list_by_report(report_id)
        total_income = self.income_repo.total_income(report_id)
        gross_expenses = self.expense_repo.total_expenses(report_id)
        recognized_expenses = self.expense_repo.total_recognized_expenses(report_id)
        taxable_income = total_income - recognized_expenses
        return FinancialSummaryResponse(
            annual_report_id=report_id,
            total_income=float(total_income),
            gross_expenses=float(gross_expenses),
            recognized_expenses=float(recognized_expenses),
            taxable_income=float(taxable_income),
            income_lines=[IncomeLineResponse.model_validate(line) for line in income_lines],
            expense_lines=[ExpenseLineResponse.model_validate(line) for line in expense_lines],
        )


__all__ = ["FinancialCrudMixin"]