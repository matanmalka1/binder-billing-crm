from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.charge.models.charge import Charge, ChargeStatus
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.repositories.client_repository import ClientRepository


class AgingReportService:
    """Aging report and financial reporting service."""

    def __init__(self, db: Session):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self.client_repo = ClientRepository(db)

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

        # Get all unpaid charges (issued but not paid)
        unpaid_charges = self.charge_repo.list_charges(
            status=ChargeStatus.ISSUED.value,
            page=1,
            page_size=10000,
        )

        # Group by client
        client_aging = {}
        
        for charge in unpaid_charges:
            if not charge.issued_at:
                continue
                
            client_id = charge.client_id
            
            if client_id not in client_aging:
                client = self.client_repo.get_by_id(client_id)
                if not client:
                    continue
                    
                client_aging[client_id] = {
                    "client_name": client.full_name,
                    "current": 0.0,
                    "days_30": 0.0,
                    "days_60": 0.0,
                    "days_90_plus": 0.0,
                    "total": 0.0,
                    "oldest_date": None,
                }

            # Calculate age of debt
            days_old = (as_of_date - charge.issued_at.date()).days
            amount = float(charge.amount)

            # Categorize by age
            if days_old <= 30:
                client_aging[client_id]["current"] += amount
            elif days_old <= 60:
                client_aging[client_id]["days_30"] += amount
            elif days_old <= 90:
                client_aging[client_id]["days_60"] += amount
            else:
                client_aging[client_id]["days_90_plus"] += amount

            client_aging[client_id]["total"] += amount

            # Track oldest invoice
            if (client_aging[client_id]["oldest_date"] is None or 
                charge.issued_at.date() < client_aging[client_id]["oldest_date"]):
                client_aging[client_id]["oldest_date"] = charge.issued_at.date()

        # Build response
        items = []
        total_outstanding = 0.0

        for client_id, data in client_aging.items():
            oldest_days = None
            if data["oldest_date"]:
                oldest_days = (as_of_date - data["oldest_date"]).days

            items.append({
                "client_id": client_id,
                "client_name": data["client_name"],
                "total_outstanding": round(data["total"], 2),
                "current": round(data["current"], 2),
                "days_30": round(data["days_30"], 2),
                "days_60": round(data["days_60"], 2),
                "days_90_plus": round(data["days_90_plus"], 2),
                "oldest_invoice_date": data["oldest_date"],
                "oldest_invoice_days": oldest_days,
            })
            
            total_outstanding += data["total"]

        # Sort by total outstanding (descending)
        items.sort(key=lambda x: x["total_outstanding"], reverse=True)

        # Calculate summary
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
        }
