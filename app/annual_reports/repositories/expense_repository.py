"""Repository for AnnualReportExpenseLine entities."""

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.annual_reports.models.annual_report_expense_line import (
    AnnualReportExpenseLine,
    ExpenseCategoryType,
)
from app.annual_reports.services.constants import default_recognition_rate


class AnnualReportExpenseRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(
        self,
        annual_report_id: int,
        category: ExpenseCategoryType,
        amount: Decimal,
        description: Optional[str] = None,
        recognition_rate: Optional[Decimal] = None,
        external_document_reference: Optional[str] = None,
        supporting_document_id: Optional[int] = None,
    ) -> AnnualReportExpenseLine:
        rate = recognition_rate if recognition_rate is not None else default_recognition_rate(category)
        line = AnnualReportExpenseLine(
            annual_report_id=annual_report_id,
            category=category,
            amount=amount,
            recognition_rate=rate,
            external_document_reference=external_document_reference,
            supporting_document_id=supporting_document_id,
            description=description,
        )
        self.db.add(line)
        self.db.flush()
        return line

    def list_by_report(self, annual_report_id: int) -> list[AnnualReportExpenseLine]:
        return (
            self.db.query(AnnualReportExpenseLine)
            .filter(AnnualReportExpenseLine.annual_report_id == annual_report_id)
            .order_by(AnnualReportExpenseLine.category.asc())
            .all()
        )

    def get_by_id(self, line_id: int) -> Optional[AnnualReportExpenseLine]:
        return (
            self.db.query(AnnualReportExpenseLine)
            .filter(AnnualReportExpenseLine.id == line_id)
            .first()
        )

    def update(self, line_id: int, **fields) -> Optional[AnnualReportExpenseLine]:
        line = self.get_by_id(line_id)
        if not line:
            return None
        for k, v in fields.items():
            if hasattr(line, k):
                setattr(line, k, v)
        self.db.flush()
        return line

    def delete(self, line_id: int) -> bool:
        # Intentional hard-delete: expense lines are user-entered data with no
        # audit trail requirement. Soft-delete would require schema migration (Sprint 10+).
        line = self.get_by_id(line_id)
        if not line:
            return False
        self.db.delete(line)
        self.db.flush()
        return True

    def total_expenses(self, annual_report_id: int) -> Decimal:
        """Sum of gross (unrecognized) expense amounts."""
        result = (
            self.db.query(func.coalesce(func.sum(AnnualReportExpenseLine.amount), 0))
            .filter(AnnualReportExpenseLine.annual_report_id == annual_report_id)
            .scalar()
        )
        return Decimal(str(result))

    def total_recognized_expenses(self, annual_report_id: int) -> Decimal:
        """Sum of amount × recognition_rate across all expense lines."""
        lines = self.list_by_report(annual_report_id)
        return sum(
            (Decimal(str(l.amount)) * Decimal(str(l.recognition_rate)) for l in lines),
            Decimal("0"),
        )


__all__ = ["AnnualReportExpenseRepository"]
