from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import BinderStatus, NotificationTrigger
from app.repositories import BinderRepository, ClientRepository, NotificationRepository
from app.services.notification_service import NotificationService
from app.services.sla_service import SLAService


class DailySLAJobService:
    """
    Daily background job for SLA monitoring and notifications.
    
    Sprint 4: Single daily job, no cron UI, no user configuration.
    """

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.client_repo = ClientRepository(db)
        self.notification_service = NotificationService(db)
        self.notification_repo = NotificationRepository(db)

    def run(self, reference_date: Optional[date] = None) -> dict:
        """
        Execute daily SLA job.
        
        Scans all active binders, evaluates SLA state, emits notifications.
        
        Returns:
            Job execution summary
        """
        if reference_date is None:
            reference_date = date.today()

        active_binders = self.binder_repo.list_active()

        approaching_count = 0
        overdue_count = 0
        ready_for_pickup_count = 0

        for binder in active_binders:
            client = self.client_repo.get_by_id(binder.client_id)
            if not client:
                continue

            if SLAService.is_overdue(binder, reference_date):
                if not self.notification_repo.exists_for_binder_trigger(
                    binder.id, NotificationTrigger.BINDER_OVERDUE
                ):
                    self.notification_service.notify_overdue(
                        binder, client, SLAService.days_overdue(binder, reference_date)
                    )
                    overdue_count += 1
                continue

            if binder.status == BinderStatus.READY_FOR_PICKUP:
                if not self.notification_repo.exists_for_binder_trigger(
                    binder.id, NotificationTrigger.BINDER_READY_FOR_PICKUP
                ):
                    self.notification_service.notify_ready_for_pickup(binder, client)
                    ready_for_pickup_count += 1
                continue

            if SLAService.is_approaching_sla(binder, reference_date):
                if not self.notification_repo.exists_for_binder_trigger(
                    binder.id, NotificationTrigger.BINDER_APPROACHING_SLA
                ):
                    self.notification_service.notify_approaching_sla(
                        binder, client, SLAService.days_remaining(binder, reference_date)
                    )
                    approaching_count += 1

        return {
            "reference_date": reference_date.isoformat(),
            "binders_scanned": len(active_binders),
            "approaching_sla_notifications": approaching_count,
            "overdue_notifications": overdue_count,
            "ready_for_pickup_notifications": ready_for_pickup_count,
        }
