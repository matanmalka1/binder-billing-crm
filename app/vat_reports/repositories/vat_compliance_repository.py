"""Repository queries used exclusively by the VAT compliance report."""

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.businesses.models.business import Business
from app.clients.models.client import Client
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem


class VatComplianceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_compliance_aggregates(self, year: int) -> list:
        """Per-business aggregates: expected periods and filed count for a given year."""
        year_str = str(year)
        filed_case = case(
            (VatWorkItem.status == VatWorkItemStatus.FILED, 1), else_=0
        )
        return (
            self.db.query(
                VatWorkItem.business_id,
                Business.client_id,
                Client.full_name.label("client_name"),
                func.count(VatWorkItem.id).label("periods_expected"),
                func.sum(filed_case).label("periods_filed"),
            )
            .join(Business, Business.id == VatWorkItem.business_id)
            .join(Client, Client.id == Business.client_id)
            .filter(
                func.substr(VatWorkItem.period, 1, 4) == year_str,
                VatWorkItem.deleted_at.is_(None),
                Business.deleted_at.is_(None),
                Client.deleted_at.is_(None),
            )
            .group_by(VatWorkItem.business_id, Business.client_id, Client.full_name)
            .order_by(Client.full_name)
            .all()
        )

    def get_filed_items(self, year: int) -> list:
        """All filed work items for a year with filing timestamps."""
        year_str = str(year)
        return (
            self.db.query(
                VatWorkItem.business_id,
                VatWorkItem.period,
                VatWorkItem.filed_at,
            )
            .filter(
                func.substr(VatWorkItem.period, 1, 4) == year_str,
                VatWorkItem.status == VatWorkItemStatus.FILED,
                VatWorkItem.filed_at.isnot(None),
                VatWorkItem.deleted_at.is_(None),
            )
            .all()
        )

    def get_stale_pending(self) -> list:
        """All PENDING_MATERIALS items across all years, ordered by updated_at."""
        return (
            self.db.query(
                VatWorkItem.business_id,
                Business.client_id,
                Client.full_name.label("client_name"),
                VatWorkItem.period,
                VatWorkItem.updated_at,
            )
            .join(Business, Business.id == VatWorkItem.business_id)
            .join(Client, Client.id == Business.client_id)
            .filter(
                VatWorkItem.status == VatWorkItemStatus.PENDING_MATERIALS,
                VatWorkItem.deleted_at.is_(None),
                Business.deleted_at.is_(None),
                Client.deleted_at.is_(None),
            )
            .order_by(VatWorkItem.updated_at.asc())
            .all()
        )
