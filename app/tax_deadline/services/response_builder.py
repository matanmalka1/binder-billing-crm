"""Response assembly for tax deadline API payloads."""

from sqlalchemy.orm import Session

from app.actions.report_deadline_actions import get_tax_deadline_actions
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.common.enums import AdvancePaymentFrequency, VatType
from app.advance_payments.models.advance_payment import AdvancePayment
from app.tax_deadline.models.tax_deadline import TaxDeadline
from app.vat_reports.models.vat_work_item import VatWorkItem
from app.tax_deadline.schemas.tax_deadline import TaxDeadlineResponse
from app.tax_deadline.services.urgency import compute_deadline_urgency
from app.users.models.user import UserRole


class TaxDeadlineResponseBuilder:
    def __init__(self, db: Session):
        self.db = db
        self.client_repo = ClientRecordRepository(db)
        self.legal_entity_repo = LegalEntityRepository(db)

    def build(
        self,
        deadline: TaxDeadline,
        *,
        client_name: str | None = None,
        office_client_number: int | None = None,
        user_role: UserRole | str | None = None,
    ) -> TaxDeadlineResponse:
        response = TaxDeadlineResponse.model_validate(deadline)
        resolved_name = (
            client_name
            if client_name is not None
            else self._resolve_client_name(deadline.client_record_id)
        )
        if resolved_name is not None:
            response.client_name = resolved_name
        response.office_client_number = office_client_number
        response.urgency_level = compute_deadline_urgency(deadline)
        response.available_actions = get_tax_deadline_actions(deadline, user_role=user_role)
        response.period_months_count = self._resolve_period_months_count(deadline)
        return response

    def _resolve_client_name(self, client_record_id: int) -> str | None:
        client_record = self.client_repo.get_by_id(client_record_id)
        if not client_record:
            return None
        legal_entity = self.legal_entity_repo.get_by_id(client_record.legal_entity_id)
        return legal_entity.official_name if legal_entity else None

    def _resolve_period_months_count(self, deadline: TaxDeadline) -> int | None:
        if not deadline.period:
            return None
        if deadline.deadline_type.value == "vat":
            if deadline.vat_work_item_id:
                item = self.db.get(VatWorkItem, deadline.vat_work_item_id)
                if item:
                    return 2 if item.period_type == VatType.BIMONTHLY else 1
            return None
        if deadline.deadline_type.value != "advance_payment":
            return None
        if deadline.advance_payment_id:
            payment = self.db.get(AdvancePayment, deadline.advance_payment_id)
            if payment:
                return payment.period_months_count
        month = int(deadline.period[-2:])
        record = self.client_repo.get_by_id(deadline.client_record_id)
        entity = self.legal_entity_repo.get_by_id(record.legal_entity_id) if record else None
        if entity and entity.advance_payment_frequency == AdvancePaymentFrequency.BIMONTHLY and month % 2 == 1:
            return 2
        return 1
