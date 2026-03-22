from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.charge.schemas.charge import BulkChargeFailedItem
from app.charge.services.billing_service import BillingService


class BulkBillingService:
    """Bulk charge action logic."""

    def __init__(self, db: Session):
        self.billing = BillingService(db)

    def bulk_action(
        self,
        charge_ids: list[int],
        action: str,
        actor_id: Optional[int] = None,
        cancellation_reason: Optional[str] = None,
    ) -> tuple[list[int], list[BulkChargeFailedItem]]:
        """
        Apply action to multiple charges.

        Returns (succeeded_ids, failed_items). Never raises on partial failure.
        """
        succeeded: list[int] = []
        failed: list[BulkChargeFailedItem] = []

        for charge_id in charge_ids:
            try:
                if action == "issue":
                    self.billing.issue_charge(charge_id, actor_id=actor_id)
                elif action == "mark-paid":
                    self.billing.mark_charge_paid(charge_id, actor_id=actor_id)
                elif action == "cancel":
                    self.billing.cancel_charge(
                        charge_id,
                        actor_id=actor_id,
                        reason=cancellation_reason,
                    )
                succeeded.append(charge_id)
            except AppError as exc:
                failed.append(BulkChargeFailedItem(id=charge_id, error=exc.message))
            except Exception:
                failed.append(BulkChargeFailedItem(id=charge_id, error="אירעה שגיאה פנימית"))

        return succeeded, failed
