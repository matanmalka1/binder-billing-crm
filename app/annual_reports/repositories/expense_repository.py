"""Repository for AnnualReportExpenseLine entities."""

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.annual_reports.models.annual_report_expense_line import (
    AnnualReportExpenseLine,
    ExpenseCategoryType,
)


class AnnualReportExpenseRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(
        self,
        annual_report_id: int,
        category: ExpenseCategoryType,
        amount: Decimal,
        description: Optional[str] = None,
    ) -> AnnualReportExpenseLine:
        line = AnnualReportExpenseLine(
            annual_report_id=annual_report_id,
            category=category,
            amount=amount,
            description=description,
        )
        self.db.add(line)
        self.db.commit()
        self.db.refresh(line)
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
        self.db.commit()
        self.db.refresh(line)
        return line

    def delete(self, line_id: int) -> bool:
        line = self.get_by_id(line_id)
        if not line:
            return False
        self.db.delete(line)
        self.db.commit()
        return True

    def total_expenses(self, annual_report_id: int) -> Decimal:
        result = (
            self.db.query(func.coalesce(func.sum(AnnualReportExpenseLine.amount), 0))
            .filter(AnnualReportExpenseLine.annual_report_id == annual_report_id)
            .scalar()
        )
        return Decimal(str(result))


__all__ = ["AnnualReportExpenseRepository"]
