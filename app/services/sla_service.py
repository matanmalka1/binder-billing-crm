from datetime import date
from typing import Optional

from app.models import Binder, BinderStatus


class SLAService:
    """Centralized SLA and overdue logic (derived, not persisted)."""

    @staticmethod
    def is_overdue(binder: Binder, reference_date: Optional[date] = None) -> bool:
        """
        Check if binder is overdue.
        
        A binder is OVERDUE if:
        - today > expected_return_at
        - status != RETURNED
        """
        if reference_date is None:
            reference_date = date.today()
        
        return (
            binder.expected_return_at < reference_date
            and binder.status != BinderStatus.RETURNED
        )

    @staticmethod
    def days_overdue(binder: Binder, reference_date: Optional[date] = None) -> int:
        """
        Calculate days overdue (>= 0).
        
        Returns 0 if not overdue.
        """
        if reference_date is None:
            reference_date = date.today()
        
        if not SLAService.is_overdue(binder, reference_date):
            return 0
        
        delta = reference_date - binder.expected_return_at
        return max(0, delta.days)

    @staticmethod
    def is_due_today(binder: Binder, reference_date: Optional[date] = None) -> bool:
        """Check if binder is due today."""
        if reference_date is None:
            reference_date = date.today()
        
        return (
            binder.expected_return_at == reference_date
            and binder.status != BinderStatus.RETURNED
        )