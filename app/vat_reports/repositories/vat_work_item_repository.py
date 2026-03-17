"""Repository for VatWorkItem and VatAuditLog entities."""

from typing import Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.utils.time_utils import utcnow
from app.vat_reports.models.vat_audit_log import VatAuditLog
from app.vat_reports.models.vat_enums import FilingMethod, VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem


class VatWorkItemRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── VatWorkItem CRUD ─────────────────────────────────────────────────────

    def create(
        self,
        client_id: int,
        period: str,
        created_by: int,
        status: VatWorkItemStatus = VatWorkItemStatus.MATERIAL_RECEIVED,
        pending_materials_note: Optional[str] = None,
        assigned_to: Optional[int] = None,
    ) -> VatWorkItem:
        item = VatWorkItem(
            client_id=client_id,
            period=period,
            created_by=created_by,
            status=status,
            pending_materials_note=pending_materials_note,
            assigned_to=assigned_to,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_by_id(self, item_id: int) -> Optional[VatWorkItem]:
        return self.db.query(VatWorkItem).filter(VatWorkItem.id == item_id).first()

    def get_by_client_period(self, client_id: int, period: str) -> Optional[VatWorkItem]:
        return (
            self.db.query(VatWorkItem)
            .filter(VatWorkItem.client_id == client_id, VatWorkItem.period == period)
            .first()
        )

    def list_by_client(self, client_id: int) -> list[VatWorkItem]:
        return (
            self.db.query(VatWorkItem)
            .filter(VatWorkItem.client_id == client_id)
            .order_by(VatWorkItem.period.desc())
            .all()
        )

    def list_by_status(
        self,
        status: VatWorkItemStatus,
        page: int = 1,
        page_size: int = 50,
        period: Optional[str] = None,
        client_ids: Optional[list[int]] = None,
    ) -> list[VatWorkItem]:
        offset = (page - 1) * page_size
        q = self.db.query(VatWorkItem).filter(VatWorkItem.status == status)
        if period:
            q = q.filter(VatWorkItem.period == period)
        if client_ids is not None:
            q = q.filter(VatWorkItem.client_id.in_(client_ids))
        return q.order_by(VatWorkItem.period.desc()).offset(offset).limit(page_size).all()

    def count_by_status(
        self,
        status: VatWorkItemStatus,
        period: Optional[str] = None,
        client_ids: Optional[list[int]] = None,
    ) -> int:
        q = self.db.query(VatWorkItem).filter(VatWorkItem.status == status)
        if period:
            q = q.filter(VatWorkItem.period == period)
        if client_ids is not None:
            q = q.filter(VatWorkItem.client_id.in_(client_ids))
        return q.count()

    def list_all(
        self,
        page: int = 1,
        page_size: int = 50,
        period: Optional[str] = None,
        client_ids: Optional[list[int]] = None,
    ) -> list[VatWorkItem]:
        offset = (page - 1) * page_size
        q = self.db.query(VatWorkItem)
        if period:
            q = q.filter(VatWorkItem.period == period)
        if client_ids is not None:
            q = q.filter(VatWorkItem.client_id.in_(client_ids))
        return q.order_by(VatWorkItem.period.desc()).offset(offset).limit(page_size).all()

    def count_all(
        self,
        period: Optional[str] = None,
        client_ids: Optional[list[int]] = None,
    ) -> int:
        q = self.db.query(VatWorkItem)
        if period:
            q = q.filter(VatWorkItem.period == period)
        if client_ids is not None:
            q = q.filter(VatWorkItem.client_id.in_(client_ids))
        return q.count()

    def count_by_period_not_filed(self, period: str) -> int:
        """Count VAT work items for a given period that are not yet filed."""
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.period == period,
                VatWorkItem.status != VatWorkItemStatus.FILED,
            )
            .count()
        )

    def sum_net_vat_by_client_year(self, client_id: int, tax_year: int) -> Optional[float]:
        """Sum net_vat for all periods of a given tax year for a client."""
        row = (
            self.db.query(sa_func.sum(VatWorkItem.net_vat).label("total_vat"))
            .filter(
                VatWorkItem.client_id == client_id,
                sa_func.substr(VatWorkItem.period, 1, 4) == str(tax_year),
            )
            .one_or_none()
        )
        if row and row[0] is not None:
            return float(row[0])
        return None

    def list_not_filed_for_period(self, period: str, limit: int = 3) -> list[VatWorkItem]:
        """Return unfiled VAT work items for a period, ordered by creation date."""
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.period == period,
                VatWorkItem.status != VatWorkItemStatus.FILED,
            )
            .order_by(VatWorkItem.created_at.asc())
            .limit(limit)
            .all()
        )

    def update_status(
        self,
        item_id: int,
        new_status: VatWorkItemStatus,
        **extra_fields,
    ) -> Optional[VatWorkItem]:
        item = self.get_by_id(item_id)
        if not item:
            return None
        item.status = new_status
        item.updated_at = utcnow()
        for key, value in extra_fields.items():
            if hasattr(item, key):
                setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_vat_totals(
        self,
        item_id: int,
        total_output_vat: float,
        total_input_vat: float,
    ) -> Optional[VatWorkItem]:
        item = self.get_by_id(item_id)
        if not item:
            return None
        item.total_output_vat = total_output_vat
        item.total_input_vat = total_input_vat
        item.net_vat = total_output_vat - total_input_vat
        item.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(item)
        return item

    def mark_filed(
        self,
        item_id: int,
        final_vat_amount: float,
        filing_method: FilingMethod,
        filed_by: int,
        is_overridden: bool = False,
        override_justification: Optional[str] = None,
        submission_reference: Optional[str] = None,
        is_amendment: bool = False,
        amends_item_id: Optional[int] = None,
    ) -> Optional[VatWorkItem]:
        item = self.get_by_id(item_id)
        if not item:
            return None
        item.status = VatWorkItemStatus.FILED
        item.final_vat_amount = final_vat_amount
        item.filing_method = filing_method
        item.filed_at = utcnow()
        item.filed_by = filed_by
        item.is_overridden = is_overridden
        item.override_justification = override_justification
        item.submission_reference = submission_reference
        item.is_amendment = is_amendment
        item.amends_item_id = amends_item_id
        item.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(item)
        return item

    # ── VatAuditLog ──────────────────────────────────────────────────────────

    def append_audit(
        self,
        work_item_id: int,
        performed_by: int,
        action: str,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        note: Optional[str] = None,
    ) -> VatAuditLog:
        entry = VatAuditLog(
            work_item_id=work_item_id,
            performed_by=performed_by,
            action=action,
            old_value=old_value,
            new_value=new_value,
            note=note,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_audit_trail(self, work_item_id: int) -> list[VatAuditLog]:
        return (
            self.db.query(VatAuditLog)
            .filter(VatAuditLog.work_item_id == work_item_id)
            .order_by(VatAuditLog.performed_at.asc())
            .all()
        )
