from datetime import timezone

from sqlalchemy.orm import Session

from app.audit.constants import (
    ACTION_CREATED,
    ACTION_ISSUED,
    ACTION_PAID,
    ACTION_STATUS_CHANGED,
    ACTION_UPDATED,
    ENTITY_ANNUAL_REPORT,
    ENTITY_CHARGE,
    ENTITY_CLIENT,
)
from app.audit.models.entity_audit_log import EntityAuditLog
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.annual_reports.repositories.annual_report_repository import AnnualReportRepository
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.repositories.client_record_repository import get_full_records_bulk

_ACTIVITY_LIMIT = 5
_ACTIVITY_FETCH_LIMIT = 20

_ACTION_LABELS = {
    ACTION_CREATED: "נוצרה רשומה חדשה",
    ACTION_UPDATED: "עודכנה רשומה",
    ACTION_ISSUED: "נפתח חיוב חדש",
    ACTION_PAID: "סומן כתשלום שהתקבל",
    ACTION_STATUS_CHANGED: "עודכן סטטוס",
}

_ENTITY_LABELS = {
    ENTITY_ANNUAL_REPORT: 'דוח שנתי',
    ENTITY_CHARGE: 'חיוב',
    ENTITY_CLIENT: 'לקוח',
}

_ACTIVITY_TYPES = {
    ACTION_CREATED: "created",
    ACTION_ISSUED: "charge",
    ACTION_PAID: "done",
    ACTION_STATUS_CHANGED: "done",
    ACTION_UPDATED: "updated",
}


class RecentActivityService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EntityAuditLogRepository(db)
        self.charge_repo = ChargeRepository(db)
        self.report_repo = AnnualReportRepository(db)

    def build(self) -> list[dict]:
        rows = self.repo.list_recent(_ACTIVITY_FETCH_LIMIT)
        client_names = self._client_names(rows)
        return [
            self._serialize(row, client_names[row.id])
            for row in rows
            if row.id in client_names
        ][:_ACTIVITY_LIMIT]

    def _serialize(self, row: EntityAuditLog, client_name: str) -> dict:
        return {
            "id": row.id,
            "time": self._format_time(row),
            "label": self._label(row),
            "client_name": client_name,
            "activity_type": _ACTIVITY_TYPES.get(row.action, "updated"),
        }

    def _client_names(self, rows: list[EntityAuditLog]) -> dict[int, str]:
        activity_client_ids = {
            row.id: client_id
            for row in rows
            if (client_id := self._client_record_id(row)) is not None
        }
        records = get_full_records_bulk(self.db, list(activity_client_ids.values()))
        return {
            activity_id: records[client_id]["full_name"]
            for activity_id, client_id in activity_client_ids.items()
            if client_id in records
        }

    def _client_record_id(self, row: EntityAuditLog) -> int | None:
        if row.entity_type == ENTITY_CLIENT:
            return row.entity_id
        if row.entity_type == ENTITY_CHARGE:
            charge = self.charge_repo.get_by_id(row.entity_id)
            return charge.client_record_id if charge else None
        if row.entity_type == ENTITY_ANNUAL_REPORT:
            report = self.report_repo.get_by_id(row.entity_id)
            return report.client_record_id if report else None
        return None

    def _label(self, row: EntityAuditLog) -> str:
        if row.note and not row.note.startswith("{"):
            return row.note

        action = _ACTION_LABELS.get(row.action, "בוצעה פעולה")
        entity = _ENTITY_LABELS.get(row.entity_type, "רשומה")
        return f"{action} ב{entity}"

    def _format_time(self, row: EntityAuditLog) -> str:
        timestamp = row.performed_at
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone().strftime("%H:%M")
