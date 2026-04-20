"""CRUD and summary operations for annual report financial lines."""

import json
from decimal import Decimal
from typing import Optional

from app.audit.constants import (
    ACTION_EXPENSE_ADDED, ACTION_EXPENSE_DELETED, ACTION_EXPENSE_UPDATED,
    ACTION_INCOME_ADDED, ACTION_INCOME_DELETED, ACTION_INCOME_UPDATED,
    ENTITY_ANNUAL_REPORT,
)
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.clients.models.client import ClientStatus
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.annual_reports.models.annual_report_expense_line import ExpenseCategoryType
from app.annual_reports.models.annual_report_income_line import IncomeSourceType
from app.annual_reports.schemas.annual_report_financials import (
    ExpenseLineResponse,
    FinancialSummaryResponse,
    IncomeLineResponse,
)
from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.annual_reports.services.messages import (
    CLIENT_CLOSED_CREATE_WORK_ERROR,
    CLIENT_FROZEN_CREATE_WORK_ERROR,
    EXPENSE_LINE_NOT_FOUND,
    INCOME_LINE_NOT_FOUND,
    INVALID_EXPENSE_CATEGORY_ERROR,
    INVALID_INCOME_SOURCE_ERROR,
)


class FinancialCrudMixin:
    def _assert_client_allows_create(self, client_record_id: int) -> None:
        client_record = ClientRecordRepository(self.db).get_by_id(client_record_id)
        if client_record and client_record.status == ClientStatus.CLOSED:
            raise ForbiddenError(CLIENT_CLOSED_CREATE_WORK_ERROR, "CLIENT.CLOSED")
        if client_record and client_record.status == ClientStatus.FROZEN:
            raise ForbiddenError(CLIENT_FROZEN_CREATE_WORK_ERROR, "CLIENT.FROZEN")

    def add_income(
        self,
        report_id: int,
        source_type: str,
        amount: Decimal,
        description: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> IncomeLineResponse:
        report = self._get_report_or_raise(report_id)
        self._assert_client_allows_create(report.client_record_id)
        valid_sources = {e.value for e in IncomeSourceType}
        if source_type not in valid_sources:
            raise AppError(INVALID_INCOME_SOURCE_ERROR.format(source_type=source_type), "ANNUAL_REPORT.INVALID_TYPE")
        line = self.income_repo.add(report_id, IncomeSourceType(source_type), amount, description)
        if actor_id:
            EntityAuditLogRepository(self.db).append(
                entity_type=ENTITY_ANNUAL_REPORT, entity_id=report_id,
                performed_by=actor_id, action=ACTION_INCOME_ADDED,
                new_value=json.dumps({"source_type": source_type, "amount": str(amount)}),
            )
        return IncomeLineResponse.model_validate(line)

    def update_income(self, report_id: int, line_id: int, actor_id: Optional[int] = None, **fields) -> IncomeLineResponse:
        self._get_report_or_raise(report_id)
        if "source_type" in fields and fields["source_type"] is not None:
            valid_sources = {e.value for e in IncomeSourceType}
            if fields["source_type"] not in valid_sources:
                raise AppError(INVALID_INCOME_SOURCE_ERROR.format(source_type=fields["source_type"]), "ANNUAL_REPORT.INVALID_TYPE")
            fields["source_type"] = IncomeSourceType(fields["source_type"])
        line = self.income_repo.update(line_id, **{k: v for k, v in fields.items() if v is not None})
        if not line:
            raise NotFoundError(INCOME_LINE_NOT_FOUND.format(line_id=line_id), "ANNUAL_REPORT.LINE_NOT_FOUND")
        if actor_id:
            EntityAuditLogRepository(self.db).append(
                entity_type=ENTITY_ANNUAL_REPORT, entity_id=report_id,
                performed_by=actor_id, action=ACTION_INCOME_UPDATED,
                new_value=json.dumps({k: str(v) if v is not None else None for k, v in fields.items()}),
            )
        return IncomeLineResponse.model_validate(line)

    def delete_income(self, report_id: int, line_id: int, actor_id: Optional[int] = None) -> None:
        self._get_report_or_raise(report_id)
        if not self.income_repo.delete(line_id):
            raise NotFoundError(INCOME_LINE_NOT_FOUND.format(line_id=line_id), "ANNUAL_REPORT.LINE_NOT_FOUND")
        if actor_id:
            EntityAuditLogRepository(self.db).append(
                entity_type=ENTITY_ANNUAL_REPORT, entity_id=report_id,
                performed_by=actor_id, action=ACTION_INCOME_DELETED,
                note=f"line_id={line_id}",
            )

    def add_expense(
        self,
        report_id: int,
        category: str,
        amount: Decimal,
        description: Optional[str] = None,
        recognition_rate: Optional[Decimal] = None,
        external_document_reference: Optional[str] = None,
        supporting_document_id: Optional[int] = None,
        actor_id: Optional[int] = None,
    ) -> ExpenseLineResponse:
        report = self._get_report_or_raise(report_id)
        self._assert_client_allows_create(report.client_record_id)
        valid_categories = {e.value for e in ExpenseCategoryType}
        if category not in valid_categories:
            raise AppError(INVALID_EXPENSE_CATEGORY_ERROR.format(category=category), "ANNUAL_REPORT.INVALID_TYPE")
        line = self.expense_repo.add(
            report_id, ExpenseCategoryType(category), amount, description,
            recognition_rate, external_document_reference, supporting_document_id,
        )
        if actor_id:
            EntityAuditLogRepository(self.db).append(
                entity_type=ENTITY_ANNUAL_REPORT, entity_id=report_id,
                performed_by=actor_id, action=ACTION_EXPENSE_ADDED,
                new_value=json.dumps({"category": category, "amount": str(amount)}),
            )
        return ExpenseLineResponse.model_validate(line)

    def update_expense(self, report_id: int, line_id: int, actor_id: Optional[int] = None, **fields) -> ExpenseLineResponse:
        self._get_report_or_raise(report_id)
        if "category" in fields and fields["category"] is not None:
            valid_categories = {e.value for e in ExpenseCategoryType}
            if fields["category"] not in valid_categories:
                raise AppError(INVALID_EXPENSE_CATEGORY_ERROR.format(category=fields["category"]), "ANNUAL_REPORT.INVALID_TYPE")
            fields["category"] = ExpenseCategoryType(fields["category"])
        line = self.expense_repo.update(line_id, **{k: v for k, v in fields.items() if v is not None})
        if not line:
            raise NotFoundError(EXPENSE_LINE_NOT_FOUND.format(line_id=line_id), "ANNUAL_REPORT.LINE_NOT_FOUND")
        if actor_id:
            EntityAuditLogRepository(self.db).append(
                entity_type=ENTITY_ANNUAL_REPORT, entity_id=report_id,
                performed_by=actor_id, action=ACTION_EXPENSE_UPDATED,
                new_value=json.dumps({k: str(v) if v is not None else None for k, v in fields.items()}),
            )
        return ExpenseLineResponse.model_validate(line)

    def delete_expense(self, report_id: int, line_id: int, actor_id: Optional[int] = None) -> None:
        self._get_report_or_raise(report_id)
        if not self.expense_repo.delete(line_id):
            raise NotFoundError(EXPENSE_LINE_NOT_FOUND.format(line_id=line_id), "ANNUAL_REPORT.LINE_NOT_FOUND")
        if actor_id:
            EntityAuditLogRepository(self.db).append(
                entity_type=ENTITY_ANNUAL_REPORT, entity_id=report_id,
                performed_by=actor_id, action=ACTION_EXPENSE_DELETED,
                note=f"line_id={line_id}",
            )

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
