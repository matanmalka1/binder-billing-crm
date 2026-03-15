"""VAT Compliance Report: per-client period coverage and stale pending flags."""

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.clients.models.client import Client
from app.utils.time_utils import utcnow
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.models.vat_work_item import VatWorkItem

_STALE_DAYS = 30


class VatComplianceReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_vat_compliance_report(self, year: int) -> dict:
        year_str = str(year)

        # ── Per-client aggregates ─────────────────────────────────────────────
        filed_case = case(
            (VatWorkItem.status == VatWorkItemStatus.FILED, 1), else_=0
        )
        rows = (
            self.db.query(
                VatWorkItem.client_id,
                Client.full_name.label("client_name"),
                func.count(VatWorkItem.id).label("periods_expected"),
                func.sum(filed_case).label("periods_filed"),
            )
            .join(Client, Client.id == VatWorkItem.client_id)
            .filter(func.substr(VatWorkItem.period, 1, 4) == year_str)
            .group_by(VatWorkItem.client_id, Client.full_name)
            .order_by(Client.full_name)
            .all()
        )

        # ── On-time / late counts require per-row data ────────────────────────
        filed_items = (
            self.db.query(
                VatWorkItem.client_id,
                VatWorkItem.period,
                VatWorkItem.filed_at,
            )
            .filter(
                func.substr(VatWorkItem.period, 1, 4) == year_str,
                VatWorkItem.status == VatWorkItemStatus.FILED,
                VatWorkItem.filed_at.isnot(None),
            )
            .all()
        )

        on_time_map: dict[int, int] = {}
        late_map: dict[int, int] = {}
        for fi in filed_items:
            period_month = int(fi.period[5:7])
            period_year = int(fi.period[:4])
            filed_dt = fi.filed_at
            is_late = (filed_dt.year > period_year) or (
                filed_dt.year == period_year and filed_dt.month > period_month
            )
            bucket = late_map if is_late else on_time_map
            bucket[fi.client_id] = bucket.get(fi.client_id, 0) + 1

        items = []
        for r in rows:
            expected = int(r.periods_expected)
            filed = int(r.periods_filed or 0)
            on_time = on_time_map.get(r.client_id, 0)
            late = late_map.get(r.client_id, 0)
            items.append(
                {
                    "client_id": r.client_id,
                    "client_name": r.client_name,
                    "periods_expected": expected,
                    "periods_filed": filed,
                    "periods_open": expected - filed,
                    "on_time_count": on_time,
                    "late_count": late,
                    "compliance_rate": round(filed / expected * 100, 2) if expected else 0.0,
                }
            )

        # ── Stale PENDING_MATERIALS ───────────────────────────────────────────
        threshold = utcnow().replace(tzinfo=None)
        stale_rows = (
            self.db.query(
                VatWorkItem.client_id,
                Client.full_name.label("client_name"),
                VatWorkItem.period,
                VatWorkItem.updated_at,
            )
            .join(Client, Client.id == VatWorkItem.client_id)
            .filter(VatWorkItem.status == VatWorkItemStatus.PENDING_MATERIALS)
            .order_by(VatWorkItem.updated_at.asc())
            .all()
        )

        stale_pending = []
        for sr in stale_rows:
            updated = sr.updated_at
            days_pending = (threshold - updated).days
            if days_pending >= _STALE_DAYS:
                stale_pending.append(
                    {
                        "client_id": sr.client_id,
                        "client_name": sr.client_name,
                        "period": sr.period,
                        "days_pending": days_pending,
                    }
                )

        return {
            "year": year,
            "total_clients": len(items),
            "items": items,
            "stale_pending": stale_pending,
        }
