"""VAT turnover lookup for advance payment context."""

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.vat_reports.models.vat_work_item import VatWorkItem


class TurnoverLookupRepository:
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

        rows = (
            self.db.query(VatWorkItem.id, VatWorkItem.total_output_net)
            .filter(
                VatWorkItem.client_record_id == client_record_id,
                VatWorkItem.period.in_(periods),
                VatWorkItem.deleted_at.is_(None),
            )
            .all()
        )
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

        rows = (
            self.db.query(VatWorkItem.id, VatWorkItem.period, VatWorkItem.total_output_net)
            .filter(
                VatWorkItem.client_record_id == client_record_id,
                VatWorkItem.period.in_(all_periods),
                VatWorkItem.deleted_at.is_(None),
            )
            .all()
        )
        by_period = {r.period: (r.id, Decimal(str(r.total_output_net))) for r in rows}

        result: dict[str, tuple[Optional[Decimal], Optional[int]]] = {}
        for period, months_count in periods:
            year = int(period[:4])
            start_month = int(period[5:7])
            sub_periods = [
                f"{year}-{str(start_month + i).zfill(2)}"
                for i in range(months_count)
            ]
            found = [by_period[p] for p in sub_periods if p in by_period]
            if not found:
                result[period] = (None, None)
            else:
                total = sum(t for _, t in found)
                primary_id = found[0][0]
                result[period] = (total, primary_id)
        return result
