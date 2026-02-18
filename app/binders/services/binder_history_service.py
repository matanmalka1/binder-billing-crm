from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import Binder
from app.binders.models.binder_status_log import BinderStatusLog
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_status_log_repository import BinderStatusLogRepository


class BinderHistoryService:
    """Binder audit history read service."""

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.log_repo = BinderStatusLogRepository(db)

    def get_binder_history(self, binder_id: int) -> Optional[tuple[Binder, list[BinderStatusLog]]]:
        """
        Get binder and its audit history.
        
        Returns:
            (binder, logs) or None if binder not found
        """
        binder = self.binder_repo.get_by_id(binder_id)
        
        if not binder:
            return None
        
        logs = self.log_repo.list_by_binder(binder_id)
        return binder, logs
