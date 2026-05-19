from datetime import UTC

from sqlalchemy.orm import Session

from app.annual_reports.repositories.annual_report_repository import (
    AnnualReportRepository,
)
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
from app.binders.models.binder import BinderStatus
from app.binders.models.binder_status_log import BinderStatusLog
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import (
    BinderStatusLogRepository,
)
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.repositories.client_record_read_repository import get_full_records_bulk

_ACTIVITY_LIMIT = 5
_ACTIVITY_FETCH_LIMIT = 20

_ENTITY_LABELS = {
    ENTITY_ANNUAL_REPORT: "דוח שנתי",
    ENTITY_CHARGE: "חיוב",
    ENTITY_CLIENT: "לקוח",
}

_ACTION_LABELS = {
    ACTION_CREATED: {
        ENTITY_ANNUAL_REPORT: "נוצר דוח שנתי חדש",
        ENTITY_CHARGE: "נוצר חיוב חדש",
        ENTITY_CLIENT: "נוצר לקוח חדש",
    },
    ACTION_UPDATED: {
        ENTITY_ANNUAL_REPORT: "עודכן דוח שנתי",
        ENTITY_CHARGE: "עודכן חיוב",
        ENTITY_CLIENT: "עודכן לקוח",
    },
    ACTION_ISSUED: {ENTITY_CHARGE: "נפתח חיוב חדש"},
    ACTION_PAID: {ENTITY_CHARGE: "חיוב סומן כשולם"},
    ACTION_STATUS_CHANGED: {
        ENTITY_ANNUAL_REPORT: "עודכן סטטוס דוח שנתי",
        ENTITY_CHARGE: "עודכן סטטוס חיוב",
        ENTITY_CLIENT: "עודכן סטטוס לקוח",
    },
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
        self.binder_repo = BinderRepository(db)
        self.binder_status_log_repo = BinderStatusLogRepository(db)

    def build(self) -> list[dict]:
        audit_rows = self.repo.list_recent(_ACTIVITY_FETCH_LIMIT)
        binder_rows = self.binder_status_log_repo.list_recent(_ACTIVITY_FETCH_LIMIT)
        client_names = self._client_names(audit_rows, binder_rows)

        items = [
            (row.performed_at, self._serialize(row, client_names[row.id]))
            for row in audit_rows
            if row.id in client_names
        ]
        items.extend(
            (
                row.changed_at,
                self._serialize_binder(row, client_names[f"binder:{row.id}"]),
            )
            for row in binder_rows
            if f"binder:{row.id}" in client_names
        )

        return [item for _, item in sorted(items, key=lambda pair: pair[0], reverse=True)][
            :_ACTIVITY_LIMIT
        ]

    def _serialize(self, row: EntityAuditLog, client_name: str) -> dict:
        return {
            "id": row.id,
            "date": self._format_date(row),
            "time": self._format_time(row),
            "label": self._label(row),
            "client_name": client_name,
            "href": self._href(row),
            "activity_type": _ACTIVITY_TYPES.get(row.action, "updated"),
        }

    def _client_names(
        self, audit_rows: list[EntityAuditLog], binder_rows: list[BinderStatusLog]
    ) -> dict[int | str, str]:
        activity_client_ids = {
            row.id: client_id
            for row in audit_rows
            if (client_id := self._client_record_id(row)) is not None
        }
        activity_client_ids.update(
            {
                f"binder:{row.id}": client_id
                for row in binder_rows
                if (client_id := self._binder_client_record_id(row)) is not None
            }
        )
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

    def _binder_client_record_id(self, row: BinderStatusLog) -> int | None:
        binder = self.binder_repo.get_by_id(row.binder_id)
        return binder.client_record_id if binder else None

    def _serialize_binder(self, row: BinderStatusLog, client_name: str) -> dict:
        return {
            "id": -row.id,
            "date": self._format_date(row),
            "time": self._format_time(row),
            "label": self._binder_label(row),
            "client_name": client_name,
            "href": f"/binders?binder_id={row.binder_id}",
            "activity_type": "done"
            if row.new_status == BinderStatus.READY_FOR_PICKUP.value
            else "updated",
        }

    def _binder_label(self, row: BinderStatusLog) -> str:
        if row.new_status == BinderStatus.READY_FOR_PICKUP.value:
            return "קלסר מוכן לאיסוף"
        if row.new_status == BinderStatus.RETURNED.value:
            return "קלסר הוחזר ללקוח"
        if row.new_status == BinderStatus.IN_OFFICE.value:
            return "קלסר הוחזר לעבודה במשרד"
        return "עודכן סטטוס קלסר"

    def _label(self, row: EntityAuditLog) -> str:
        if row.note and not row.note.startswith("{"):
            return row.note

        label_by_entity = _ACTION_LABELS.get(row.action, {})
        if row.entity_type in label_by_entity:
            return label_by_entity[row.entity_type]

        entity = _ENTITY_LABELS.get(row.entity_type, "רשומה")
        return f"בוצעה פעולה ב{entity}"

    def _href(self, row: EntityAuditLog) -> str:
        if row.entity_type == ENTITY_ANNUAL_REPORT:
            return f"/tax/reports/{row.entity_id}"
        if row.entity_type == ENTITY_CHARGE:
            return f"/charges?charge_id={row.entity_id}"
        if row.entity_type == ENTITY_CLIENT:
            return f"/clients/{row.entity_id}"
        return "/"

    def _timestamp(self, row: EntityAuditLog | BinderStatusLog):
        timestamp = getattr(row, "performed_at", None) or row.changed_at
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        return timestamp.astimezone()

    def _format_date(self, row: EntityAuditLog | BinderStatusLog) -> str:
        return self._timestamp(row).strftime("%d.%m.%Y")

    def _format_time(self, row: EntityAuditLog | BinderStatusLog) -> str:
        return self._timestamp(row).strftime("%H:%M")
