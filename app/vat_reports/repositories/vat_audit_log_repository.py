"""Repository for VatAuditLog entities."""

from typing import Optional

from sqlalchemy.orm import Session

from app.vat_reports.models.vat_audit_log import VatAuditLog


class VatAuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def append(
        self,
        work_item_id: int,
        performed_by: int,
        action: str,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        note: Optional[str] = None,
        invoice_id: Optional[int] = None,
    ) -> VatAuditLog:
        entry = VatAuditLog(
            work_item_id=work_item_id,
            performed_by=performed_by,
            action=action,
            old_value=old_value,
            new_value=new_value,
            note=note,
            invoice_id=invoice_id,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def count_audit_trail(self, work_item_id: int) -> int:
        return self.db.query(VatAuditLog).filter(VatAuditLog.work_item_id == work_item_id).count()

    def get_audit_trail(self, work_item_id: int, limit: int, offset: int) -> list[VatAuditLog]:
        return (
            self.db.query(VatAuditLog)
            .filter(VatAuditLog.work_item_id == work_item_id)
            .order_by(VatAuditLog.performed_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
