from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.actions.obligation_orchestrator import generate_client_obligations
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.services.client_onboarding_service import create_initial_binder
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.core.exceptions import ConflictError, NotFoundError
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository
from app.vat_reports.services.intake import create_work_item


@dataclass(slots=True)
class ClientOnboardingResult:
    obligations_created: int = 0
    vat_work_items_created: int = 0
    advance_payments_created: int = 0


class ClientOnboardingOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRecordRepository(db)
        self.deadline_repo = TaxDeadlineRepository(db)
        self.binder_repo = BinderRepository(db)
        self.vat_repo = VatWorkItemRepository(db)
        self.advance_repo = AdvancePaymentRepository(db)

    def run(
        self,
        client_record_id: int,
        *,
        actor_id: Optional[int],
        entity_type=None,
        reference_date: Optional[date] = None,
    ) -> ClientOnboardingResult:
        record = self.client_repo.get_by_id(client_record_id)
        if not record:
            raise NotFoundError(
                f"רשומת לקוח {client_record_id} לא נמצאה",
                "CLIENT_RECORD.NOT_FOUND",
            )
        result = ClientOnboardingResult()
        self._ensure_initial_binder(record, actor_id)
        result.obligations_created = generate_client_obligations(
            self.db,
            client_record_id,
            actor_id=actor_id,
            entity_type=entity_type,
            reference_date=reference_date,
            best_effort=False,
        )
        result.vat_work_items_created = self._sync_vat_work_items(client_record_id, actor_id)
        result.advance_payments_created = self._sync_advance_payments(client_record_id)
        return result

    def _ensure_initial_binder(self, record, actor_id: Optional[int]) -> None:
        if self.binder_repo.count_all_by_client(record.id) > 0:
            return
        create_initial_binder(self.db, record, actor_id)

    def _sync_vat_work_items(self, client_record_id: int, actor_id: Optional[int]) -> int:
        deadlines = self.deadline_repo.list_by_client_record(
            client_record_id,
            deadline_type=DeadlineType.VAT,
        )
        created = 0
        for deadline in deadlines:
            if not deadline.period:
                continue
            item = self.vat_repo.get_by_client_record_period(client_record_id, deadline.period)
            if item is None and actor_id is not None:
                try:
                    item = create_work_item(
                        self.vat_repo,
                        self.db,
                        client_record_id=client_record_id,
                        period=deadline.period,
                        created_by=actor_id,
                        mark_pending=True,
                        pending_materials_note="נוצר אוטומטית מפתיחת לקוח",
                    )
                    created += 1
                except ConflictError:
                    item = self.vat_repo.get_by_client_record_period(client_record_id, deadline.period)
            if item is not None:
                deadline.vat_work_item_id = item.id
        if deadlines:
            self.db.flush()
        return created

    def _sync_advance_payments(self, client_record_id: int) -> int:
        deadlines = self.deadline_repo.list_by_client_record(
            client_record_id,
            deadline_type=DeadlineType.ADVANCE_PAYMENT,
        )
        created = 0
        for deadline in deadlines:
            if not deadline.period:
                continue
            payment = self.advance_repo.get_by_period(client_record_id, deadline.period)
            if payment is None:
                try:
                    payment = self.advance_repo.create(
                        client_record_id=client_record_id,
                        period=deadline.period,
                        period_months_count=1,
                        due_date=deadline.due_date,
                    )
                    created += 1
                except ConflictError:
                    payment = self.advance_repo.get_by_period(client_record_id, deadline.period)
                    if payment is None:
                        raise
            if deadline.advance_payment_id is None:
                deadline.advance_payment_id = payment.id
        if deadlines:
            self.db.flush()
        return created
