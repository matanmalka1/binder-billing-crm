from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.charge.repositories.charge_repository import ChargeRepository
from app.businesses.repositories.business_repository import BusinessRepository

_AGING_CHARGE_FETCH_LIMIT = 2000


class AgingReportService:
    """Aging report and financial reporting service."""

    def __init__(self, db: Session):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self.business_repo = BusinessRepository(db)

    def generate_aging_report(
        self,
        as_of_date: Optional[date] = None,
    ) -> dict:
        """
        Generate aging report for all clients.

        Categorizes outstanding charges by age:
        - Current: 0-30 days
        - 30 days: 31-60 days
        - 60 days: 61-90 days
        - 90+ days: 91+ days
        """
        if as_of_date is None:
            as_of_date = date.today()

        all_rows = self.charge_repo.get_aging_buckets(as_of_date)
        capped = len(all_rows) > _AGING_CHARGE_FETCH_LIMIT
        rows = all_rows[:_AGING_CHARGE_FETCH_LIMIT]

        business_ids = [row.business_id for row in rows]
        business_map = {b.id: b for b in self.business_repo.list_by_ids(business_ids)}

        items = []
        total_outstanding = 0.0

        for row in rows:
            business = business_map.get(row.business_id)
            if not business:
                continue

            oldest_date = row.oldest_issued_at.date() if row.oldest_issued_at else None
            oldest_days = (as_of_date - oldest_date).days if oldest_date else None

            items.append({
                "client_id": business.client_id,
                "client_name": business.business_name,
                "total_outstanding": round(float(row.total), 2),
                "current": round(float(row.current), 2),
                "days_30": round(float(row.days_30), 2),
                "days_60": round(float(row.days_60), 2),
                "days_90_plus": round(float(row.days_90_plus), 2),
                "oldest_invoice_date": oldest_date,
                "oldest_invoice_days": oldest_days,
            })

            total_outstanding += float(row.total)

        items.sort(key=lambda x: x["total_outstanding"], reverse=True)

        summary = {
            "total_clients": len(items),
            "total_current": round(sum(item["current"] for item in items), 2),
            "total_30_days": round(sum(item["days_30"] for item in items), 2),
            "total_60_days": round(sum(item["days_60"] for item in items), 2),
            "total_90_plus": round(sum(item["days_90_plus"] for item in items), 2),
        }

        return {
            "report_date": as_of_date,
            "total_outstanding": round(total_outstanding, 2),
            "items": items,
            "summary": summary,
            "capped": capped,
            "cap_limit": _AGING_CHARGE_FETCH_LIMIT,
        }
