from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.binders.models.binder import Binder
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.models.binder import BinderStatus
from app.binders.services.operational_signals_builder import build_client_operational_signals
from app.charge.repositories.charge_repository import ChargeRepository
from app.charge.models.charge import ChargeStatus
from app.binders.services.constants import IDLE_THRESHOLD_DAYS
from app.notification.models.notification import Notification


class SignalsService:
    """
    Compute operational signals for UX.

    Signals are:
    - Derived dynamically (NOT persisted)
    - Advisory only (non-blocking)
    - Internal UX indicators
    """

    def __init__(self, db: Session):
        self.db = db
        self.binder_repo = BinderRepository(db)
        self.charge_repo = ChargeRepository(db)
        from app.permanent_documents.services.permanent_document_service import (
            PermanentDocumentService,
        )
        self.document_service = PermanentDocumentService(db)

    def is_idle_binder(
        self,
        binder: Binder,
        reference_date: Optional[date] = None,
    ) -> bool:
        if reference_date is None:
            reference_date = date.today()

        if binder.status != BinderStatus.IN_OFFICE:
            return False

        days_since_start = (reference_date - binder.period_start).days
        if days_since_start < IDLE_THRESHOLD_DAYS:
            return False

        return not self._has_recent_notification_activity(binder, reference_date)

    def _has_recent_notification_activity(
        self,
        binder: Binder,
        reference_date: date,
    ) -> bool:
        threshold_date = reference_date - timedelta(days=IDLE_THRESHOLD_DAYS)
        result = (
            self.db.query(Notification)
            .filter(
                Notification.binder_id == binder.id,
                Notification.created_at >= threshold_date,
            )
            .limit(1)
            .first()
        )
        return result is not None

    def compute_business_signals(
        self,
        business_id: int,
        reference_date: Optional[date] = None,
    ) -> dict:
        """Compute signals for a business (charges, documents)."""
        if reference_date is None:
            reference_date = date.today()

        missing_docs = self.document_service.get_missing_document_types(business_id)

        unpaid = self.charge_repo.count_charges(
            business_id=business_id,
            status=ChargeStatus.ISSUED.value,
        ) > 0

        return {
            "missing_documents": list(missing_docs),
            "unpaid_charges": unpaid,
        }

    def compute_business_operational_signals(
        self,
        business_id: int,
        reference_date: Optional[date] = None,
    ) -> dict:
        if reference_date is None:
            reference_date = date.today()
        return build_client_operational_signals(
            self.document_service,
            self.binder_repo,
            business_id=business_id,
            reference_date=reference_date,
        )
