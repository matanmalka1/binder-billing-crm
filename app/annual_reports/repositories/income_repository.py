"""Repository for AnnualReportIncomeLine entities."""

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.annual_reports.models.annual_report_income_line import (
    AnnualReportIncomeLine,
    IncomeSourceType,
)
from app.common.repositories.base_repository import BaseRepository


class AnnualReportIncomeRepository(BaseRepository[AnnualReportIncomeLine]):
    def __init__(self, db: Session):
        self.db = db

    def add_line(
        self,
        annual_report_id: int,
        source_type: IncomeSourceType,
        amount: Decimal,
        description: Optional[str] = None,
    ) -> AnnualReportIncomeLine:
        line = AnnualReportIncomeLine(
            annual_report_id=annual_report_id,
            source_type=source_type,
            amount=amount,
            description=description,
        )
        self.db.add(line)
        self.db.flush()
        return line

    def list_by_report(self, annual_report_id: int) -> list[AnnualReportIncomeLine]:
        return self.db.scalars(
            select(AnnualReportIncomeLine)
            .where(AnnualReportIncomeLine.annual_report_id == annual_report_id)
            .order_by(AnnualReportIncomeLine.source_type.asc())
        ).all()

    def get_by_id(self, line_id: int) -> Optional[AnnualReportIncomeLine]:
        return self.db.scalars(
            select(AnnualReportIncomeLine).where(AnnualReportIncomeLine.id == line_id)
        ).first()

    def update(self, line_id: int, **fields) -> Optional[AnnualReportIncomeLine]:
        line = self.get_by_id(line_id)
        if not line:
            return None
        for k, v in fields.items():
            if hasattr(line, k):
                setattr(line, k, v)
        self.db.flush()
        return line

    def delete(
        self,
        line_id: int,
        deleted_by: int | None = None,
        *,
        hard: bool = False,
    ) -> bool:
        # Intentional hard-delete: income lines are user-entered data with no
        # audit trail requirement. Soft-delete would require schema migration (Sprint 10+).
        line = self.get_by_id(line_id)
        if not line:
            return False
        self.db.delete(line)
        self.db.flush()
        return True

    def total_income(self, annual_report_id: int) -> Decimal:
        result = self.db.scalar(
            select(func.coalesce(func.sum(AnnualReportIncomeLine.amount), 0)).where(
                AnnualReportIncomeLine.annual_report_id == annual_report_id
            )
        )
        return Decimal(str(result))


__all__ = ["AnnualReportIncomeRepository"]
