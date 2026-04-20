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

    def get_by_id_for_update(self, item_id: int) -> Optional[VatWorkItem]:
        """Fetch with a row-level lock for status transitions."""
        return self._query.get_by_id_for_update(item_id)

    def get_by_client_record_period(self, client_record_id: int, period: str) -> Optional[VatWorkItem]:
        return self._query.get_by_client_record_period(client_record_id, period)

    def list_by_client_record(self, client_record_id: int, limit: int = 200) -> list[VatWorkItem]:
        return self._query.list_by_client_record(client_record_id, limit=limit)

    def list_by_business_activity(self, business_activity_id: int, limit: int = 200) -> list[VatWorkItem]:
        return self._query.list_by_business_activity(business_activity_id, limit=limit)

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

    def sum_net_vat_by_client_record_year(self, client_record_id: int, tax_year: int):
        return self._query.sum_net_vat_by_client_record_year(client_record_id, tax_year)

    def list_not_filed_for_period(self, period: str, limit: int = 3) -> list[VatWorkItem]:
        return self._query.list_not_filed_for_period(period, limit=limit)

    def create(
        self,
        client_record_id: Optional[int] = None,
        period: Optional[str] = None,
        period_type=None,
        created_by: Optional[int] = None,
        status: VatWorkItemStatus = VatWorkItemStatus.MATERIAL_RECEIVED,
        pending_materials_note: Optional[str] = None,
        assigned_to: Optional[int] = None,
    ) -> VatWorkItem:
        if client_record_id is None or period is None or period_type is None or created_by is None:
            raise TypeError("client_record_id, period, period_type, and created_by are required")
        item = VatWorkItem(
            client_record_id=client_record_id,
            period=period,
            period_type=period_type,
            created_by=created_by,
            status=status,
            pending_materials_note=pending_materials_note,
            assigned_to=assigned_to,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update_status(
        self,
        item_id: int,
        new_status: VatWorkItemStatus,
        item: Optional[VatWorkItem] = None,
        **extra_fields,
    ) -> Optional[VatWorkItem]:
        """Update status. Pass a pre-fetched (optionally locked) ``item`` to
        avoid a second SELECT and keep the lock from get_by_id_for_update() alive."""
        item = item or self.get_by_id(item_id)
        if not item:
            return None
        item.status = new_status
        item.updated_at = utcnow()
        for key, value in extra_fields.items():
            if hasattr(item, key):
                setattr(item, key, value)
        self.db.flush()
        return item

    def cancel_open_by_client_record(self, client_record_id: int) -> int:
        rows = (
            self.db.query(VatWorkItem)
            .filter(
                VatWorkItem.client_record_id == client_record_id,
                VatWorkItem.deleted_at.is_(None),
                VatWorkItem.status.notin_([VatWorkItemStatus.FILED]),
            )
            .all()
        )
        for row in rows:
            row.status = VatWorkItemStatus.CANCELED
            row.updated_at = utcnow()
        if rows:
            self.db.flush()
        return len(rows)

    def update_vat_totals(
        self,
        item_id: int,
        total_output_vat,
        total_input_vat,
        total_output_net,
        total_input_net,
    ) -> Optional[VatWorkItem]:
        from decimal import Decimal

        item = self.get_by_id(item_id)
        if not item:
            return None
        item.total_output_vat = Decimal(str(total_output_vat))
        item.total_input_vat = Decimal(str(total_input_vat))
        item.net_vat = Decimal(str(total_output_vat)) - Decimal(str(total_input_vat))
        item.total_output_net = Decimal(str(total_output_net))
        item.total_input_net = Decimal(str(total_input_net))
        item.updated_at = utcnow()
        self.db.flush()
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
        item: Optional[VatWorkItem] = None,
    ) -> Optional[VatWorkItem]:
        """File the work item. Pass a pre-fetched (optionally locked) ``item`` to
        avoid a second SELECT and keep the lock from get_by_id_for_update() alive."""
        item = item or self.get_by_id(item_id)
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
        self.db.flush()
        return item

    def append_audit(self, **kwargs) -> VatAuditLog:
        return self._audit.append(**kwargs)

    def get_audit_trail(self, work_item_id: int) -> list[VatAuditLog]:
        return self._audit.get_audit_trail(work_item_id)
