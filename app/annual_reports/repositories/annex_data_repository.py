"""Repository for AnnualReportAnnexData entities."""

from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.annual_reports.models.annual_report_annex_data import AnnualReportAnnexData
from app.annual_reports.models.annual_report_enums import AnnualReportSchedule
from app.annual_reports.models.annual_report_schedule_entry import AnnualReportScheduleEntry


class AnnexDataRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_report_and_schedule(
        self, report_id: int, schedule: AnnualReportSchedule
    ) -> list[AnnualReportAnnexData]:
        return (
            self.db.query(AnnualReportAnnexData)
            .join(AnnualReportAnnexData.schedule_entry)
            .filter(
                AnnualReportScheduleEntry.annual_report_id == report_id,
                AnnualReportScheduleEntry.schedule == schedule,
            )
            .order_by(AnnualReportAnnexData.line_number.asc())
            .all()
        )

    def get_schedule_entry(
        self, report_id: int, schedule: AnnualReportSchedule
    ) -> Optional[AnnualReportScheduleEntry]:
        return (
            self.db.query(AnnualReportScheduleEntry)
            .filter(
                AnnualReportScheduleEntry.annual_report_id == report_id,
                AnnualReportScheduleEntry.schedule == schedule,
            )
            .first()
        )

    def get_or_create_schedule_entry(
        self, report_id: int, schedule: AnnualReportSchedule
    ) -> AnnualReportScheduleEntry:
        entry = self.get_schedule_entry(report_id, schedule)
        if entry:
            return entry
        entry = AnnualReportScheduleEntry(
            annual_report_id=report_id,
            schedule=schedule,
            is_required=False,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def next_line_number(self, schedule_entry_id: int) -> int:
        current_max = (
            self.db.query(func.max(AnnualReportAnnexData.line_number))
            .filter(AnnualReportAnnexData.schedule_entry_id == schedule_entry_id)
            .scalar()
        )
        return int(current_max or 0) + 1

    def add_line(
        self,
        schedule_entry_id: int,
        line_number: int,
        data: dict,
        notes: Optional[str] = None,
    ) -> AnnualReportAnnexData:
        row = AnnualReportAnnexData(
            schedule_entry_id=schedule_entry_id,
            line_number=line_number,
            data=data,
            notes=notes,
        )
        self.db.add(row)
        self.db.flush()
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
        self.db.flush()
        return row

    def delete_line(self, line_id: int) -> bool:
        # Intentional hard-delete: annex data lines are user-entered data with no
        # audit trail requirement. Soft-delete would require schema migration (Sprint 10+).
        row = self.get_by_id(line_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.flush()
        return True

    def count_by_report_and_schedule(
        self, report_id: int, schedule: AnnualReportSchedule
    ) -> int:
        return (
            self.db.query(AnnualReportAnnexData)
            .join(AnnualReportAnnexData.schedule_entry)
            .filter(
                AnnualReportScheduleEntry.annual_report_id == report_id,
                AnnualReportScheduleEntry.schedule == schedule,
            )
            .count()
        )


__all__ = ["AnnexDataRepository"]
