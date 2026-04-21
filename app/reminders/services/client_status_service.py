from sqlalchemy.orm import Session

from app.reminders.repositories.reminder_repository import ReminderRepository


class ReminderClientStatusService:
    def __init__(self, db: Session):
        self.repo = ReminderRepository(db)

    def cancel_pending_by_client_record(self, client_record_id: int) -> int:
        return self.repo.cancel_pending_by_client_record(client_record_id)
