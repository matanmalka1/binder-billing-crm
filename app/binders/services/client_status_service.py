from sqlalchemy.orm import Session

from app.binders.repositories.binder_repository import BinderRepository


class BinderClientStatusService:
    def __init__(self, db: Session):
        self.repo = BinderRepository(db)

    def archive_in_office_by_client_record(self, client_record_id: int) -> int:
        return self.repo.archive_in_office_by_client_record(client_record_id)
