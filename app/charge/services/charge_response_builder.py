from app.actions.charge_actions import get_charge_actions
from app.charge.models.charge import Charge
from app.charge.schemas.charge import ChargeResponse, ChargeResponseSecretary
from app.charge.services.charge_query_service import ChargeQueryService
from app.users.models.user import UserRole


class ChargeResponseBuilder:
    def __init__(self, query_service: ChargeQueryService):
        self.query_service = query_service

    def build(self, charge: Charge, user_role: UserRole) -> ChargeResponse | ChargeResponseSecretary:
        schema = ChargeResponseSecretary if user_role == UserRole.SECRETARY else ChargeResponse
        data = schema.model_validate(charge).model_dump()
        business_name, office_client_number = self.query_service.enrich_charge_context(charge)
        data["business_name"] = business_name
        data["office_client_number"] = office_client_number
        data["available_actions"] = get_charge_actions(charge, user_role=user_role)
        return schema(**data)
