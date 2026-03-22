"""Repository for AnnualReportAnnexData entities."""

from typing import Optional

from sqlalchemy.orm import Session

from app.annual_reports.models.annual_report_annex_data import AnnualReportAnnexData
from app.annual_reports.models.annual_report_enums import AnnualReportSchedule


class AnnexDataRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_report_and_schedule(
        self, report_id: int, schedule: AnnualReportSchedule
    ) -> list[AnnualReportAnnexData]:
        return (
            self.db.query(AnnualReportAnnexData)
            .filter(
                AnnualReportAnnexData.annual_report_id == report_id,
                AnnualReportAnnexData.schedule == schedule,
            )
            .order_by(AnnualReportAnnexData.line_number.asc())
            .all()
        )

    def next_line_number(self, report_id: int, schedule: AnnualReportSchedule) -> int:
        rows = self.list_by_report_and_schedule(report_id, schedule)
        return (max((r.line_number for r in rows), default=0)) + 1

    def add_line(
        self,
        report_id: int,
        schedule: AnnualReportSchedule,
        line_number: int,
        data: dict,
        notes: Optional[str] = None,
    ) -> AnnualReportAnnexData:
        row = AnnualReportAnnexData(
            annual_report_id=report_id,
            schedule=schedule,
            line_number=line_number,
            data=data,
            notes=notes,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_by_id(self, line_id: int) -> Optional[AnnualReportAnnexData]:
        return (
            self.db.query(AnnualReportAnnexData)
            .filter(AnnualReportAnnexData.id == line_id)
            .first()
        )

    def update_line(
        self, line_id: int, data: dict, notes: Optional[str] = None
    ) -> Optional[AnnualReportAnnexData]:
        row = self.get_by_id(line_id)
        if not row:
            return None
        row.data = data
        if notes is not None:
            row.notes = notes
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_line(self, line_id: int) -> bool:
        # Intentional hard-delete: annex data lines are user-entered data with no
        # audit trail requirement. Soft-delete would require schema migration (Sprint 10+).
        row = self.get_by_id(line_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def count_by_report_and_schedule(
        self, report_id: int, schedule: AnnualReportSchedule
    ) -> int:
        return (
            self.db.query(AnnualReportAnnexData)
            .filter(
                AnnualReportAnnexData.annual_report_id == report_id,
                AnnualReportAnnexData.schedule == schedule,
            )
            .count()
        )


__all__ = ["AnnexDataRepository"]
