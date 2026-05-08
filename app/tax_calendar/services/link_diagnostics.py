from sqlalchemy.orm import Session

from app.advance_payments.models.advance_payment import AdvancePayment
from app.annual_reports.models.annual_report_model import AnnualReport
from app.vat_reports.models.vat_work_item import VatWorkItem


def find_active_null_tax_calendar_links(db: Session) -> dict[str, dict[str, object]]:
    def collect(model):
        rows = (
            db.query(model.id)
            .filter(model.deleted_at.is_(None))
            .filter(model.tax_calendar_entry_id.is_(None))
            .all()
        )
        ids = [row[0] for row in rows]
        return {"count": len(ids), "ids": ids}

    return {
        "vat_work_items": collect(VatWorkItem),
        "advance_payments": collect(AdvancePayment),
        "annual_reports": collect(AnnualReport),
    }
