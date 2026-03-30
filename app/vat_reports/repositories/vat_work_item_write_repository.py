"""Write operations and audit delegation for VatWorkItem entities."""

from typing import Optional

from sqlalchemy.orm import Session

from app.common.enums import SubmissionMethod
from app.utils.time_utils import utcnow
from app.vat_reports.models.vat_audit_log import VatAuditLog
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.vat_reports.repositories.vat_audit_log_repository import VatAuditLogRepository
from app.vat_reports.repositories.vat_work_item_query_repository import VatWorkItemQueryRepository


class VatWorkItemWriteRepository:
    def __init__(self, db: Session):
        self.db = db
        self._query = VatWorkItemQueryRepository(db)
        self._audit = VatAuditLogRepository(db)

    # ── Read delegation ───────────────────────────────────────────────────────

    def get_by_id(self, item_id: int) -> Optional[VatWorkItem]:
        return self._query.get_by_id(item_id)

    def get_by_business_period(self, business_id: int, period: str) -> Optional[VatWorkItem]:
        return self._query.get_by_business_period(business_id, period)

    def list_by_business(self, business_id: int, limit: int = 200) -> list[VatWorkItem]:
        return self._query.list_by_business(business_id, limit=limit)

    def list_by_status(self, status, **kwargs) -> list[VatWorkItem]:
        return self._query.list_by_status(status, **kwargs)

    def count_by_status(self, status, **kwargs) -> int:
        return self._query.count_by_status(status, **kwargs)

    def list_all(self, **kwargs) -> list[VatWorkItem]:
        return self._query.list_all(**kwargs)

    def count_all(self, **kwargs) -> int:
        return self._query.count_all(**kwargs)

    def count_by_period_not_filed(self, period: str) -> int:
        return self._query.count_by_period_not_filed(period)

    def sum_net_vat_by_business_year(self, business_id: int, tax_year: int):
        return self._query.sum_net_vat_by_business_year(business_id, tax_year)

    def list_not_filed_for_period(self, period: str, limit: int = 3) -> list[VatWorkItem]:
        return self._query.list_not_filed_for_period(period, limit=limit)

    def create(
        self,
        business_id: int,
        period: str,
        period_type,
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
        submission_method: SubmissionMethod,
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
        item.submission_method = submission_method
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

    def append_audit(self, **kwargs) -> VatAuditLog:
        return self._audit.append(**kwargs)

    def get_audit_trail(self, work_item_id: int) -> list[VatAuditLog]:
        return self._audit.get_audit_trail(work_item_id)
