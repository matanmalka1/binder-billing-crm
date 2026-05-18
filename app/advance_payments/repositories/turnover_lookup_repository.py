"""VAT turnover lookup for advance payment context."""

from decimal import Decimal
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.repositories.base_repository import BaseRepository
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem

# Only FILED items represent settled, authoritative turnover figures.
_FINAL_STATUSES = [VatWorkItemStatus.FILED]
_PENDING_STATUSES = [VatWorkItemStatus.READY_FOR_REVIEW]


class TurnoverLookupRepository(BaseRepository[VatWorkItem]):
    """Read total_output_net from vat_work_items for advance payment period."""

    def __init__(self, db: Session):
        self.db = db

    def get_turnover_for_period(
        self,
        client_record_id: int,
        period: str,
        period_months_count: int = 1,
    ) -> tuple[Optional[Decimal], Optional[int]]:
        """Return (total_output_net, vat_work_item_id) for the period.

        For bi-monthly advances, sums both months' vat_work_items.
        Returns (None, None) if no filed/submitted vat_work_items found.
        """
        year = int(period[:4])
        start_month = int(period[5:7])
        periods = [
            f"{year}-{str(start_month + i).zfill(2)}"
            for i in range(period_months_count)
        ]

        rows = self.db.execute(
            select(VatWorkItem.id, VatWorkItem.total_output_net).where(
                VatWorkItem.client_record_id == client_record_id,
                VatWorkItem.period.in_(periods),
                VatWorkItem.status.in_(_FINAL_STATUSES),
                VatWorkItem.deleted_at.is_(None),
            )
        ).all()
        if not rows:
            return None, None

        total = sum(Decimal(str(r.total_output_net)) for r in rows)
        # For snapshot FK, use first item (canonical period start)
        primary_id = rows[0].id
        return total, primary_id

    def get_turnover_for_many(
        self,
        client_record_id: int,
        periods: list[tuple[str, int]],
    ) -> dict[str, tuple[Optional[Decimal], Optional[int]]]:
        """Batch lookup: {period: (turnover, vat_work_item_id)}.

        periods is list of (period_str, period_months_count).
        """
        all_periods = set()
        for period, months_count in periods:
            year = int(period[:4])
            start_month = int(period[5:7])
            for i in range(months_count):
                all_periods.add(f"{year}-{str(start_month + i).zfill(2)}")

        rows = self.db.execute(
            select(
                VatWorkItem.id, VatWorkItem.period, VatWorkItem.total_output_net
            ).where(
                VatWorkItem.client_record_id == client_record_id,
                VatWorkItem.period.in_(all_periods),
                VatWorkItem.status.in_(_FINAL_STATUSES),
                VatWorkItem.deleted_at.is_(None),
            )
        ).all()
        by_period = {r.period: (r.id, Decimal(str(r.total_output_net))) for r in rows}

        result: dict[str, tuple[Optional[Decimal], Optional[int]]] = {}
        for period, months_count in periods:
            year = int(period[:4])
            start_month = int(period[5:7])
            sub_periods = [
                f"{year}-{str(start_month + i).zfill(2)}" for i in range(months_count)
            ]
            found = [by_period[p] for p in sub_periods if p in by_period]
            if not found:
                result[period] = (None, None)
            else:
                total = sum(t for _, t in found)
                primary_id = found[0][0]
                result[period] = (total, primary_id)
        return result

    def get_prefill_turnover(
        self,
        client_record_id: int,
        period: str,
        period_months_count: int = 1,  # accepted for API symmetry; VatWorkItem has no period_months_count col
    ) -> tuple[
        Optional[Decimal], Optional[int], Literal["vat_filed", "vat_pending", "none"]
    ]:
        """Return (total_output_net, vat_work_item_id, source) for prefill.

        Checks FILED first, then READY_FOR_REVIEW. Matches by period string only.
        """
        for statuses, source in [
            (_FINAL_STATUSES, "vat_filed"),
            (_PENDING_STATUSES, "vat_pending"),
        ]:
            row = self.db.execute(
                select(VatWorkItem.id, VatWorkItem.total_output_net).where(
                    VatWorkItem.client_record_id == client_record_id,
                    VatWorkItem.period == period,
                    VatWorkItem.status.in_(statuses),
                    VatWorkItem.deleted_at.is_(None),
                )
            ).first()
            if row is not None:
                return Decimal(str(row.total_output_net)), row.id, source
        return None, None, "none"
