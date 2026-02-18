from datetime import date
from typing import Optional

from sqlalchemy import and_

from app.models import Binder, BinderStatus


class SLAService:
    """Centralized SLA and overdue logic (derived, not persisted)."""

    SLA_TOTAL_DAYS = 90
    APPROACHING_THRESHOLD_DAY = 75
    APPROACHING_DAYS_REMAINING_MAX = SLA_TOTAL_DAYS - APPROACHING_THRESHOLD_DAY

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
    def days_remaining(binder: Binder, reference_date: Optional[date] = None) -> int:
        """Calculate days remaining until expected return (>= 0)."""
        if reference_date is None:
            reference_date = date.today()

        delta = binder.expected_return_at - reference_date
        return max(0, delta.days)

    @staticmethod
    def is_approaching_sla(binder: Binder, reference_date: Optional[date] = None) -> bool:
        """
        Check if binder is approaching SLA threshold.

        Approaching window (Sprint 4): within the last 15 days before expected_return_at.
        """
        if reference_date is None:
            reference_date = date.today()

        if binder.status == BinderStatus.RETURNED:
            return False

        if SLAService.is_overdue(binder, reference_date):
            return False

        days_remaining = SLAService.days_remaining(binder, reference_date)
        return 0 < days_remaining <= SLAService.APPROACHING_DAYS_REMAINING_MAX

    @staticmethod
    def derive_sla_state(binder: Binder, reference_date: Optional[date] = None) -> str:
        """Derive UI-friendly SLA state label: on_track | approaching | overdue."""
        if reference_date is None:
            reference_date = date.today()

        if SLAService.is_overdue(binder, reference_date):
            return "overdue"

        if SLAService.is_approaching_sla(binder, reference_date):
            return "approaching"

        return "on_track"

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

    @staticmethod
    def overdue_filter(reference_date: date):
        """Shared ORM filter for overdue binders."""
        return and_(
            Binder.expected_return_at < reference_date,
            Binder.status != BinderStatus.RETURNED,
        )

    @staticmethod
    def due_today_filter(reference_date: date):
        """Shared ORM filter for binders due today."""
        return and_(
            Binder.expected_return_at == reference_date,
            Binder.status != BinderStatus.RETURNED,
        )
