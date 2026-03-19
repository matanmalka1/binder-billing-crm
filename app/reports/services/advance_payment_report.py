from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePayment, AdvancePaymentStatus
from app.clients.models.client import Client


class AdvancePaymentReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_collections_report(self, year: int, month: Optional[int]) -> dict:
        query = (
            self.db.query(
                AdvancePayment.client_id,
                Client.full_name.label("client_name"),
                func.coalesce(func.sum(AdvancePayment.expected_amount), 0).label("total_expected"),
                func.coalesce(func.sum(AdvancePayment.paid_amount), 0).label("total_paid"),
                func.coalesce(
                    func.sum(
                        case(
                            (func.lower(AdvancePayment.status) == AdvancePaymentStatus.OVERDUE.value, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("overdue_count"),
            )
            .join(Client, Client.id == AdvancePayment.client_id)
            .filter(AdvancePayment.year == year)
        )
        if month is not None:
            query = query.filter(AdvancePayment.month == month)
        rows = query.group_by(AdvancePayment.client_id, Client.full_name).all()

        items = [
            {
                "client_id": r.client_id,
                "client_name": r.client_name,
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
