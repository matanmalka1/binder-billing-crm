from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.binders.models.binder import BinderStatus
from app.notification.models.notification import NotificationTrigger
from app.binders.repositories.binder_repository import BinderRepository
from app.clients.repositories.client_repository import ClientRepository
from app.notification.repositories.notification_repository import NotificationRepository
from app.notification.services.notification_service import NotificationService
from app.binders.services.sla_service import SLAService

logger = get_logger(__name__)


class DailySLAJobService:
    """
    Daily background job for SLA monitoring and notifications.
    
    Sprint 4: Single daily job, no cron UI, no user configuration.
    Sprint 5: Hardened with graceful error handling.
    """

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.client_repo = ClientRepository(db)
        self.notification_service = NotificationService(db)
        self.notification_repo = NotificationRepository(db)

    def run(self, reference_date: Optional[date] = None) -> dict:
        """
        Execute daily SLA job with graceful error handling.
        
        Logs errors without crashing. Safe to retry.
        
        Returns:
            Job execution summary
        """
        if reference_date is None:
            reference_date = date.today()

        logger.info(f"Starting daily SLA job for {reference_date}")

        approaching_count = 0
        overdue_count = 0
        ready_for_pickup_count = 0
        errors = 0

        try:
            active_binders = self.binder_repo.list_active()
            logger.info(f"Scanning {len(active_binders)} active binders")
        except Exception as e:
            logger.error("Failed to fetch active binders", exc_info=e)
            return {
                "reference_date": reference_date.isoformat(),
                "status": "failed",
                "error": "Failed to fetch binders",
            }

        for binder in active_binders:
            try:
                client = self.client_repo.get_by_id(binder.client_id)
                if not client:
                    logger.warning(f"Client {binder.client_id} not found for binder {binder.id}")
                    errors += 1
                    continue

                if SLAService.is_overdue(binder, reference_date):
                    if not self.notification_repo.exists_for_binder_trigger(
                        binder.id, NotificationTrigger.BINDER_OVERDUE
                    ):
                        try:
                            self.notification_service.notify_overdue(
                                binder, client, SLAService.days_overdue(binder, reference_date)
                            )
                            overdue_count += 1
                        except Exception as e:
                            logger.error(
                                f"Failed to send overdue notification for binder {binder.id}",
                                exc_info=e,
                            )
                            errors += 1
                    continue

                if binder.status == BinderStatus.READY_FOR_PICKUP:
                    if not self.notification_repo.exists_for_binder_trigger(
                        binder.id, NotificationTrigger.BINDER_READY_FOR_PICKUP
                    ):
                        try:
                            self.notification_service.notify_ready_for_pickup(binder, client)
                            ready_for_pickup_count += 1
                        except Exception as e:
                            logger.error(
                                f"Failed to send ready notification for binder {binder.id}",
                                exc_info=e,
                            )
                            errors += 1
                    continue

                if SLAService.is_approaching_sla(binder, reference_date):
                    if not self.notification_repo.exists_for_binder_trigger(
                        binder.id, NotificationTrigger.BINDER_APPROACHING_SLA
                    ):
                        try:
                            self.notification_service.notify_approaching_sla(
                                binder, client, SLAService.days_remaining(binder, reference_date)
                            )
                            approaching_count += 1
                        except Exception as e:
                            logger.error(
                                f"Failed to send approaching notification for binder {binder.id}",
                                exc_info=e,
                            )
                            errors += 1

            except Exception as e:
                logger.error(f"Error processing binder {binder.id}", exc_info=e)
                errors += 1
                continue

        result = {
            "reference_date": reference_date.isoformat(),
            "binders_scanned": len(active_binders),
            "approaching_sla_notifications": approaching_count,
            "overdue_notifications": overdue_count,
            "ready_for_pickup_notifications": ready_for_pickup_count,
            "errors": errors,
            "status": "completed" if errors == 0 else "completed_with_errors",
        }

        logger.info(f"Daily SLA job completed: {result}")
        return result
