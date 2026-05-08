from decimal import Decimal
from typing import Optional

from app.audit.constants import ACTION_EXPENSE_ADDED, ACTION_EXPENSE_DELETED, ACTION_EXPENSE_UPDATED
from app.audit.constants import ACTION_INCOME_ADDED, ACTION_INCOME_DELETED, ACTION_INCOME_UPDATED
from app.audit.constants import ENTITY_ANNUAL_REPORT
from app.audit.services.entity_audit_writer import EntityAuditWriter
from app.clients.enums import ClientStatus
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.annual_reports.models.annual_report_expense_line import ExpenseCategoryType
from app.annual_reports.models.annual_report_income_line import IncomeSourceType
from app.annual_reports.schemas.annual_report_financials import ExpenseLineResponse, FinancialSummaryResponse, IncomeLineResponse
from app.annual_reports.services.financial_audit_snapshots import audit_scalar, expense_line_snapshot, income_line_snapshot
from app.annual_reports.services.financial_summary_builder import build_financial_summary
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
        EntityAuditWriter(self.db).append(
            ENTITY_ANNUAL_REPORT, report_id, actor_id, ACTION_INCOME_ADDED,
            new_value={"source_type": source_type, "amount": str(amount), "description": description},
        )
        return IncomeLineResponse.model_validate(line)

    def update_income(self, report_id: int, line_id: int, actor_id: Optional[int] = None, **fields) -> IncomeLineResponse:
        self._get_report_or_raise(report_id)
        if "source_type" in fields and fields["source_type"] is not None:
            valid_sources = {e.value for e in IncomeSourceType}
            if fields["source_type"] not in valid_sources:
                raise AppError(INVALID_INCOME_SOURCE_ERROR.format(source_type=fields["source_type"]), "ANNUAL_REPORT.INVALID_TYPE")
            fields["source_type"] = IncomeSourceType(fields["source_type"])
        old_line = self.income_repo.get_by_id(line_id)
        old_value = income_line_snapshot(old_line) if old_line else None
        line = self.income_repo.update(line_id, **{k: v for k, v in fields.items() if v is not None})
        if not line:
            raise NotFoundError(INCOME_LINE_NOT_FOUND.format(line_id=line_id), "ANNUAL_REPORT.LINE_NOT_FOUND")
        EntityAuditWriter(self.db).append(
            ENTITY_ANNUAL_REPORT, report_id, actor_id, ACTION_INCOME_UPDATED,
            old_value=old_value,
            new_value={k: audit_scalar(v) for k, v in fields.items()},
        )
        return IncomeLineResponse.model_validate(line)

    def delete_income(self, report_id: int, line_id: int, actor_id: Optional[int] = None) -> None:
        self._get_report_or_raise(report_id)
        line = self.income_repo.get_by_id(line_id)
        old_value = income_line_snapshot(line) if line else None
        if not self.income_repo.delete(line_id):
            raise NotFoundError(INCOME_LINE_NOT_FOUND.format(line_id=line_id), "ANNUAL_REPORT.LINE_NOT_FOUND")
        EntityAuditWriter(self.db).append(
            ENTITY_ANNUAL_REPORT, report_id, actor_id, ACTION_INCOME_DELETED,
            old_value=old_value, note=f"line_id={line_id}",
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
        EntityAuditWriter(self.db).append(
            ENTITY_ANNUAL_REPORT, report_id, actor_id, ACTION_EXPENSE_ADDED,
            new_value={"category": category, "amount": str(amount), "description": description},
        )
        return ExpenseLineResponse.model_validate(line)

    def update_expense(self, report_id: int, line_id: int, actor_id: Optional[int] = None, **fields) -> ExpenseLineResponse:
        self._get_report_or_raise(report_id)
        if "category" in fields and fields["category"] is not None:
            valid_categories = {e.value for e in ExpenseCategoryType}
            if fields["category"] not in valid_categories:
                raise AppError(INVALID_EXPENSE_CATEGORY_ERROR.format(category=fields["category"]), "ANNUAL_REPORT.INVALID_TYPE")
            fields["category"] = ExpenseCategoryType(fields["category"])
        old_line = self.expense_repo.get_by_id(line_id)
        old_value = expense_line_snapshot(old_line) if old_line else None
        line = self.expense_repo.update(line_id, **{k: v for k, v in fields.items() if v is not None})
        if not line:
            raise NotFoundError(EXPENSE_LINE_NOT_FOUND.format(line_id=line_id), "ANNUAL_REPORT.LINE_NOT_FOUND")
        EntityAuditWriter(self.db).append(
            ENTITY_ANNUAL_REPORT, report_id, actor_id, ACTION_EXPENSE_UPDATED,
            old_value=old_value,
            new_value={k: audit_scalar(v) for k, v in fields.items()},
        )
        return ExpenseLineResponse.model_validate(line)

    def delete_expense(self, report_id: int, line_id: int, actor_id: Optional[int] = None) -> None:
        self._get_report_or_raise(report_id)
        line = self.expense_repo.get_by_id(line_id)
        old_value = expense_line_snapshot(line) if line else None
        if not self.expense_repo.delete(line_id):
            raise NotFoundError(EXPENSE_LINE_NOT_FOUND.format(line_id=line_id), "ANNUAL_REPORT.LINE_NOT_FOUND")
        EntityAuditWriter(self.db).append(
            ENTITY_ANNUAL_REPORT, report_id, actor_id, ACTION_EXPENSE_DELETED,
            old_value=old_value, note=f"line_id={line_id}",
        )

    def get_financial_summary(self, report_id: int) -> FinancialSummaryResponse:
        return build_financial_summary(self, report_id)


__all__ = ["FinancialCrudMixin"]
