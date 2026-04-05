from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.businesses.models.business import Business
from app.businesses.repositories.business_repository import BusinessRepository
from app.binders.services.signals_service import SignalsService

_HAS_SIGNALS_FETCH_LIMIT = 1000


class BusinessBulkService:
    """Bulk status updates, signal-based filtering, and paginated list for businesses."""

    def __init__(self, db: Session):
        self.db = db
        self.business_repo = BusinessRepository(db)
        self.signals_service = SignalsService(db)

    def list_businesses(
        self,
        status: Optional[str] = None,
        business_type: Optional[str] = None,
        search: Optional[str] = None,
        has_signals: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        reference_date: Optional[date] = None,
    ) -> tuple[list[Business], int]:
        """List businesses with pagination and optional filters.

        Note: has_signals filtering is capped at _HAS_SIGNALS_FETCH_LIMIT — known
        architectural debt (Sprint 10+). Signals are computed in memory.
        """
        if has_signals is None:
            items = self.business_repo.list(
                status=status, business_type=business_type, search=search,
                page=page, page_size=page_size,
            )
            total = self.business_repo.count(
                status=status, business_type=business_type, search=search,
            )
            return items, total

        total_count = self.business_repo.count(
            status=status, business_type=business_type, search=search,
        )
        self.check_signal_limit(total_count)

        base = self.business_repo.list(
            status=status, business_type=business_type, search=search,
            page=1, page_size=_HAS_SIGNALS_FETCH_LIMIT,
        )
        filtered = [b for b in base if self._has_signals(b.id, reference_date) == has_signals]
        total = len(filtered)
        offset = (page - 1) * page_size
        return filtered[offset: offset + page_size], total

    def check_signal_limit(self, total_count: int) -> None:
        """Raise AppError if total exceeds the fetch limit for signal filtering."""
        from app.core.exceptions import AppError
        if total_count > _HAS_SIGNALS_FETCH_LIMIT:
            raise AppError(
                f"מספר העסקים ({total_count}) חורג מהמגבלה לסינון לפי איתותים "
                f"({_HAS_SIGNALS_FETCH_LIMIT}). יש להשתמש בפילטרים נוספים.",
                "BUSINESS.SIGNAL_FILTER_LIMIT",
            )

    def _has_signals(self, business_id: int, reference_date: Optional[date] = None) -> bool:
        signals = self.signals_service.compute_business_signals(
            business_id=business_id, reference_date=reference_date,
        )
        return bool(
            signals.get("missing_documents")
            or signals.get("unpaid_charges")
            or signals.get("binder_signals")
        )
