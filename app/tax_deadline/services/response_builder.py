"""Response assembly for tax deadline API payloads."""

from sqlalchemy.orm import Session

from app.actions.report_deadline_actions import get_tax_deadline_actions
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.clients.repositories.legal_entity_repository import LegalEntityRepository
from app.tax_deadline.models.tax_deadline import TaxDeadline
from app.tax_deadline.schemas.tax_deadline import TaxDeadlineResponse
from app.tax_deadline.services.urgency import compute_deadline_urgency
from app.users.models.user import UserRole


class TaxDeadlineResponseBuilder:
    def __init__(self, db: Session):
        self.client_repo = ClientRecordRepository(db)
        self.legal_entity_repo = LegalEntityRepository(db)

    def build(
        self,
        deadline: TaxDeadline,
        *,
        client_name: str | None = None,
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
        response.urgency_level = compute_deadline_urgency(deadline)
        response.available_actions = get_tax_deadline_actions(deadline, user_role=user_role)
        return response

    def _resolve_client_name(self, client_record_id: int) -> str | None:
        client_record = self.client_repo.get_by_id(client_record_id)
        if not client_record:
            return None
        legal_entity = self.legal_entity_repo.get_by_id(client_record.legal_entity_id)
        return legal_entity.official_name if legal_entity else None
