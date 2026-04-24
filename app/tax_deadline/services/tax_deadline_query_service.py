from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus, UrgencyLevel
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.services.constants import (
    FAR_FUTURE_DATE,
    URGENCY_WARNING_DAYS,
)
from app.tax_deadline.services.urgency import compute_deadline_urgency


class TaxDeadlineQueryService:
    """Read-only query methods for tax deadlines."""

    def __init__(self, db: Session):
        self.db = db
        self.deadline_repo = TaxDeadlineRepository(db)
        self.business_repo = BusinessRepository(db)
        self.client_record_repo = ClientRecordRepository(db)

    def list_deadlines(
        self,
        client_record_id: Optional[int],
        business_name: Optional[str],
        status: Optional[str],
        deadline_type: Optional[DeadlineType],
        page: int = 1,
        page_size: int = 50,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        period: Optional[str] = None,
    ) -> tuple[list[TaxDeadline], int]:
        """Route branching logic: by client, by business name, or all pending."""
        if client_record_id:
            client_record_id = self.client_record_repo.get_by_id(client_record_id).id
            items = self.deadline_repo.list_by_client_record(
                client_record_id, status, deadline_type,
                due_from=due_from, due_to=due_to, period=period,
            )
            total = len(items)
            offset = (page - 1) * page_size
            return items[offset: offset + page_size], total
        if business_name:
            items = self.get_deadlines_by_business_name(business_name, status, deadline_type)
            total = len(items)
            offset = (page - 1) * page_size
            return items[offset: offset + page_size], total
        return self.list_all(
            status=status, deadline_type=deadline_type, page=page, page_size=page_size,
            due_from=due_from, due_to=due_to, period=period,
        )

    def list_all_pending(
        self,
        page: int = 1,
        page_size: int = 50,
        deadline_type: Optional[DeadlineType] = None,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        period: Optional[str] = None,
    ) -> tuple[list[TaxDeadline], int]:
        """Return paginated pending deadlines with SQL-level pagination."""
        effective_from = due_from if due_from is not None else date.today()
        effective_to = due_to if due_to is not None else FAR_FUTURE_DATE
        total = self.deadline_repo.count_filtered(
            status=TaxDeadlineStatus.PENDING,
            deadline_type=deadline_type,
            due_from=effective_from,
            due_to=effective_to,
            period=period,
        )
        items = self.deadline_repo.list_filtered(
            status=TaxDeadlineStatus.PENDING,
            deadline_type=deadline_type,
            due_from=effective_from,
            due_to=effective_to,
            period=period,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return items, total

    def list_all(
        self,
        *,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
        page: int = 1,
        page_size: int = 50,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        period: Optional[str] = None,
    ) -> tuple[list[TaxDeadline], int]:
        """Return paginated deadlines for the global list while preserving pending-by-default behavior."""
        if status in (None, "", TaxDeadlineStatus.PENDING, TaxDeadlineStatus.PENDING.value):
            return self.list_all_pending(
                page=page, page_size=page_size, deadline_type=deadline_type,
                due_from=due_from, due_to=due_to, period=period,
            )

        total = self.deadline_repo.count_filtered(
            status=status, deadline_type=deadline_type,
            due_from=due_from, due_to=due_to, period=period,
        )
        items = self.deadline_repo.list_filtered(
            status=status,
            deadline_type=deadline_type,
            due_from=due_from,
            due_to=due_to,
            period=period,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return items, total

    def get_upcoming_deadlines(
        self,
        days_ahead: int = 7,
        reference_date: Optional[date] = None,
    ) -> list[TaxDeadline]:
        """Get pending deadlines within the next N days."""
        if reference_date is None:
            reference_date = date.today()
        to_date = reference_date + timedelta(days=days_ahead)
        return self.deadline_repo.list_pending_due_by_date(reference_date, to_date)

    def get_overdue_deadlines(
        self,
        reference_date: Optional[date] = None,
    ) -> list[TaxDeadline]:
        """Get all overdue pending deadlines."""
        if reference_date is None:
            reference_date = date.today()
        return self.deadline_repo.list_overdue(reference_date)

    def compute_urgency(
        self,
        deadline: TaxDeadline,
        reference_date: Optional[date] = None,
    ) -> UrgencyLevel:
        """Compute urgency level for a deadline."""
        return compute_deadline_urgency(deadline, reference_date)

    def get_deadlines_by_business_name(
        self,
        business_name: str,
        status: Optional[str] = None,
        deadline_type: Optional[DeadlineType] = None,
    ) -> list[TaxDeadline]:
        """Get deadlines filtered by business name substring."""
        businesses = self.business_repo.list(search=business_name, page=1, page_size=500)
        if not businesses:
            return []
        client_record_ids = list({b.client_record_id for b in businesses})
        return self.deadline_repo.list_by_client_ids(client_record_ids, status, deadline_type)

    def get_timeline(self, client_record_id: int) -> list:
        """Return deadlines for a client sorted by due_date asc with days_remaining and milestone_label."""
        from app.tax_deadline.services.timeline_service import build_timeline
        return build_timeline(client_record_id, self.db, self.deadline_repo)

    def build_client_name_map(self, deadlines: list[TaxDeadline]) -> dict[int, str]:
        """Return {client_record_id: client_full_name} for the given deadlines."""
        return {
            record.id: legal_entity.official_name
            for record, legal_entity in self._get_client_context_rows(deadlines)
        }

    def build_client_context_map(self, deadlines: list[TaxDeadline]) -> dict[int, dict[str, str | int | None]]:
        """Return client display context keyed by client_record_id for the given deadlines."""
        return {
            record.id: {
                "full_name": legal_entity.official_name,
                "office_client_number": record.office_client_number,
            }
            for record, legal_entity in self._get_client_context_rows(deadlines)
        }

    def _get_client_context_rows(self, deadlines: list[TaxDeadline]) -> list[tuple]:
        client_record_ids = list({d.client_record_id for d in deadlines})
        records = self.client_record_repo.list_by_ids(client_record_ids) if client_record_ids else []
        legal_repo = LegalEntityRepository(self.db)
        return [
            (record, legal_entity)
            for record in records
            if (legal_entity := legal_repo.get_by_id(record.legal_entity_id)) is not None
        ]

    def get_urgent_deadlines_summary(
        self,
        reference_date: Optional[date] = None,
    ) -> dict:
        """Get summary of urgent and upcoming deadlines for the dashboard."""
        if reference_date is None:
            reference_date = date.today()

        upcoming = self.get_upcoming_deadlines(URGENCY_WARNING_DAYS, reference_date)
        overdue = self.get_overdue_deadlines(reference_date)

        urgent = []
        for deadline in overdue:
            urgent.append({
                "deadline": deadline,
                "urgency_level": UrgencyLevel.OVERDUE,
                "days_remaining": (deadline.due_date - reference_date).days,
            })

        for deadline in upcoming:
            urgency = self.compute_urgency(deadline, reference_date)
            if urgency in (UrgencyLevel.CRITICAL, UrgencyLevel.WARNING):
                urgent.append({
                    "deadline": deadline,
                    "urgency_level": urgency,
                    "days_remaining": (deadline.due_date - reference_date).days,
                })

        return {"urgent": urgent, "upcoming": upcoming}
