from sqlalchemy.orm import Session

from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


class TaxDeadlineClientStatusService:
    def __init__(self, db: Session):
        self.repo = TaxDeadlineRepository(db)

    def cancel_pending_by_client_record(self, client_record_id: int) -> int:
        return self.repo.cancel_pending_by_client_record(client_record_id)
