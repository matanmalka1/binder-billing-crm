"""VAT Compliance Report: per-client period coverage and stale pending flags."""

from datetime import date

from sqlalchemy.orm import Session

from app.reports.constants import VAT_STALE_PENDING_DAYS
from app.utils.time_utils import utcnow
from app.vat_reports.repositories.vat_compliance_repository import VatComplianceRepository


class VatComplianceReportService:
    def __init__(self, db: Session):
        self.repo = VatComplianceRepository(db)

    def get_vat_compliance_report(self, year: int) -> dict:
        rows = self.repo.get_compliance_aggregates(year)
        filed_items = self.repo.get_filed_items(year)

        # ── On-time / late counts per business ───────────────────────────────
        on_time_map: dict[int, int] = {}
        late_map: dict[int, int] = {}
        for fi in filed_items:
            period_year = int(fi.period[:4])
            period_month = int(fi.period[5:7])
            # Israeli VAT deadline: 15th of the month following the period end
            deadline_year = period_year if period_month < 12 else period_year + 1
            deadline_month = (period_month % 12) + 1
            deadline = date(deadline_year, deadline_month, 15)
            filed_date = fi.filed_at.date() if hasattr(fi.filed_at, "date") else fi.filed_at
            is_late = filed_date > deadline
            bucket = late_map if is_late else on_time_map
            bucket[fi.client_record_id] = bucket.get(fi.client_record_id, 0) + 1

        items = []
        for r in rows:
            expected = int(r.periods_expected)
            filed = int(r.periods_filed or 0)
            on_time = on_time_map.get(r.client_record_id, 0)
            late = late_map.get(r.client_record_id, 0)
            items.append(
                {
                    "client_record_id": r.client_record_id,
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
        stale_pending = []
        for sr in self.repo.get_stale_pending(year):
            days_pending = (threshold - sr.updated_at).days
            if days_pending >= VAT_STALE_PENDING_DAYS:
                stale_pending.append(
                    {
                        "client_record_id": sr.client_record_id,
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
