"""Repository queries used exclusively by the VAT compliance report."""

from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.clients.repositories.active_client_scope import scope_to_active_clients_stmt
from app.common.repositories.base_repository import BaseRepository
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem


class VatComplianceRepository(BaseRepository[VatWorkItem]):
    def __init__(self, db: Session):
        self.db = db

    def get_compliance_aggregates(self, year: int) -> list:
        """Per-client aggregates: expected periods and filed count for a given year."""
        year_str = str(year)
        filed_case = case((VatWorkItem.status == VatWorkItemStatus.FILED, 1), else_=0)
        stmt = (
            scope_to_active_clients_stmt(
                select(
                    VatWorkItem.client_record_id,
                    VatWorkItem.period_type,
                    func.count(VatWorkItem.id).label("periods_expected"),
                    func.sum(filed_case).label("periods_filed"),
                ),
                VatWorkItem,
            )
            .where(
                func.substr(VatWorkItem.period, 1, 4) == year_str,
                VatWorkItem.deleted_at.is_(None),
            )
            .group_by(VatWorkItem.client_record_id, VatWorkItem.period_type)
            .order_by(VatWorkItem.client_record_id, VatWorkItem.period_type)
        )
        return self.db.execute(stmt).all()

    def get_filed_items(self, year: int) -> list:
        """All filed work items for a year with filing timestamps."""
        year_str = str(year)
        stmt = scope_to_active_clients_stmt(
            select(
                VatWorkItem.client_record_id,
                VatWorkItem.period_type,
                VatWorkItem.period,
                VatWorkItem.filed_at,
            ),
            VatWorkItem,
        ).where(
            func.substr(VatWorkItem.period, 1, 4) == year_str,
            VatWorkItem.status == VatWorkItemStatus.FILED,
            VatWorkItem.filed_at.isnot(None),
            VatWorkItem.deleted_at.is_(None),
        )
        return self.db.execute(stmt).all()

    def get_overdue_unfiled(self, reference_date: date) -> list[VatWorkItem]:
        """Work items whose period has passed and are not yet FILED.

        Returns full VatWorkItem rows so callers can read due_date_effective
        without issuing per-row queries.
        """
        stmt = (
            scope_to_active_clients_stmt(
                select(VatWorkItem),
                VatWorkItem,
            )
            .where(
                VatWorkItem.status != VatWorkItemStatus.FILED,
                VatWorkItem.deleted_at.is_(None),
                func.substr(VatWorkItem.period, 1, 7)
                < reference_date.strftime("%Y-%m"),
            )
            .order_by(VatWorkItem.period.asc())
        )
        return list(self.db.scalars(stmt))

    def get_stale_pending(self, year: int) -> list:
        """All PENDING_MATERIALS items for a year, ordered by updated_at."""
        year_str = str(year)
        stmt = (
            scope_to_active_clients_stmt(
                select(
                    VatWorkItem.client_record_id,
                    VatWorkItem.period,
                    VatWorkItem.updated_at,
                ),
                VatWorkItem,
            )
            .where(
                VatWorkItem.status == VatWorkItemStatus.PENDING_MATERIALS,
                func.substr(VatWorkItem.period, 1, 4) == year_str,
                VatWorkItem.deleted_at.is_(None),
            )
            .order_by(VatWorkItem.updated_at.asc())
        )
        return self.db.execute(stmt).all()
