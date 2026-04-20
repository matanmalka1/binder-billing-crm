from typing import Optional

from sqlalchemy.orm import Session

from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.clients.repositories.client_repository import ClientRepository


class AdvancePaymentReportService:
    def __init__(self, db: Session):
        self.repo = AdvancePaymentRepository(db)
        self.client_repo = ClientRepository(db)

    def get_collections_report(self, year: int, month: Optional[int]) -> dict:
        rows = self.repo.get_collections_aggregates(year, month)
        client_record_ids = [row.client_record_id for row in rows]
        clients = {client.id: client for client in self.client_repo.list_by_ids(client_record_ids)}

        items = [
            {
                "client_record_id": r.client_record_id,
                "client_name": clients[r.client_record_id].full_name if r.client_record_id in clients else f"לקוח #{r.client_record_id}",
                "total_expected": float(r.total_expected),
                "total_paid": float(r.total_paid),
                "overdue_count": int(r.overdue_count),
                "gap": float(r.total_expected) - float(r.total_paid),
            }
            for r in rows
        ]

        total_expected = sum(i["total_expected"] for i in items)
        total_paid = sum(i["total_paid"] for i in items)
        collection_rate = round(total_paid / total_expected * 100, 2) if total_expected else 0.0
        total_gap = total_expected - total_paid

        return {
            "year": year,
            "month": month,
            "total_expected": total_expected,
            "total_paid": total_paid,
            "collection_rate": collection_rate,
            "total_gap": total_gap,
            "items": items,
        }
