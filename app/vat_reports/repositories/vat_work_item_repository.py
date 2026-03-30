"""Repository for VatWorkItem entities."""

from typing import Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.common.enums import SubmissionMethod
from app.utils.time_utils import utcnow
from app.vat_reports.models.vat_audit_log import VatAuditLog
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.repositories.vat_audit_log_repository import VatAuditLogRepository


class VatWorkItemRepository:
    def __init__(self, db: Session):
        self.db = db
        self._audit = VatAuditLogRepository(db)

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def create(
        self,
        business_id: int,
        period: str,
        period_type,                            # VatType snapshot
        created_by: int,
        status: VatWorkItemStatus = VatWorkItemStatus.MATERIAL_RECEIVED,
        pending_materials_note: Optional[str] = None,
        assigned_to: Optional[int] = None,
    ) -> VatWorkItem:
        item = VatWorkItem(
            business_id=business_id,
            period=period,
            period_type=period_type,
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
        return (
            self.db.query(VatWorkItem)
            .filter(VatWorkItem.id == item_id, VatWorkItem.deleted_at.is_(None))
            .first()
        )

    def get_by_business_period(self, business_id: int, period: str) -> Optional[VatWorkItem]:
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.business_id == business_id,
                VatWorkItem.period == period,
                VatWorkItem.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_business(self, business_id: int, limit: int = 200) -> list[VatWorkItem]:
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.business_id == business_id,
                VatWorkItem.deleted_at.is_(None),
            )
            .order_by(VatWorkItem.period.desc())
            .limit(limit)
            .all()
        )

    def list_by_status(
        self,
        status: VatWorkItemStatus,
        page: int = 1,
        page_size: int = 20,
        period: Optional[str] = None,
        business_ids: Optional[list[int]] = None,
    ) -> list[VatWorkItem]:
        offset = (page - 1) * page_size
        q = (
            self.db.query(VatWorkItem)
            .filter(VatWorkItem.status == status, VatWorkItem.deleted_at.is_(None))
        )
        if period:
            q = q.filter(VatWorkItem.period == period)
        if business_ids is not None:
            q = q.filter(VatWorkItem.business_id.in_(business_ids))
        return q.order_by(VatWorkItem.period.desc()).offset(offset).limit(page_size).all()

    def count_by_status(
        self,
        status: VatWorkItemStatus,
        period: Optional[str] = None,
        business_ids: Optional[list[int]] = None,
    ) -> int:
        q = (
            self.db.query(VatWorkItem)
            .filter(VatWorkItem.status == status, VatWorkItem.deleted_at.is_(None))
        )
        if period:
            q = q.filter(VatWorkItem.period == period)
        if business_ids is not None:
            q = q.filter(VatWorkItem.business_id.in_(business_ids))
        return q.count()

    def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        period: Optional[str] = None,
        business_ids: Optional[list[int]] = None,
    ) -> list[VatWorkItem]:
        offset = (page - 1) * page_size
        q = self.db.query(VatWorkItem).filter(VatWorkItem.deleted_at.is_(None))
        if period:
            q = q.filter(VatWorkItem.period == period)
        if business_ids is not None:
            q = q.filter(VatWorkItem.business_id.in_(business_ids))
        return q.order_by(VatWorkItem.period.desc()).offset(offset).limit(page_size).all()

    def count_all(
        self,
        period: Optional[str] = None,
        business_ids: Optional[list[int]] = None,
    ) -> int:
        q = self.db.query(VatWorkItem).filter(VatWorkItem.deleted_at.is_(None))
        if period:
            q = q.filter(VatWorkItem.period == period)
        if business_ids is not None:
            q = q.filter(VatWorkItem.business_id.in_(business_ids))
        return q.count()

    def count_by_period_not_filed(self, period: str) -> int:
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.period == period,
                VatWorkItem.status != VatWorkItemStatus.FILED,
                VatWorkItem.deleted_at.is_(None),
            )
            .count()
        )

    def sum_net_vat_by_business_year(self, business_id: int, tax_year: int) -> Optional[float]:
        row = (
            self.db.query(sa_func.sum(VatWorkItem.net_vat).label("total_vat"))
            .filter(
                VatWorkItem.business_id == business_id,
                sa_func.substr(VatWorkItem.period, 1, 4) == str(tax_year),
                VatWorkItem.deleted_at.is_(None),
            )
            .one_or_none()
        )
        return float(row[0]) if row and row[0] is not None else None

    def list_not_filed_for_period(self, period: str, limit: int = 3) -> list[VatWorkItem]:
        return (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.period == period,
                VatWorkItem.status != VatWorkItemStatus.FILED,
                VatWorkItem.deleted_at.is_(None),
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
        total_output_net: float,
        total_input_net: float,
    ) -> Optional[VatWorkItem]:
        item = self.get_by_id(item_id)
        if not item:
            return None
        item.total_output_vat = total_output_vat
        item.total_input_vat = total_input_vat
        item.net_vat = total_output_vat - total_input_vat
        item.total_output_net = total_output_net
        item.total_input_net = total_input_net
        item.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(item)
        return item

    def mark_filed(
        self,
        item_id: int,
        final_vat_amount: float,
        submission_method: SubmissionMethod,    # שם חדש — לא FilingMethod
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
        item.submission_method = submission_method   # שדה חדש
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

    # ── VatAuditLog (delegated to VatAuditLogRepository) ─────────────────────

    def append_audit(self, **kwargs) -> VatAuditLog:
        return self._audit.append(**kwargs)

    def get_audit_trail(self, work_item_id: int) -> list[VatAuditLog]:
        return self._audit.get_audit_trail(work_item_id)
