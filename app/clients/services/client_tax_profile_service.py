from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, NotFoundError
from app.clients.models.client_tax_profile import ClientTaxProfile, VatType
from app.clients.repositories.client_repository import ClientRepository
from app.clients.repositories.client_tax_profile_repository import ClientTaxProfileRepository


class ClientTaxProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ClientTaxProfileRepository(db)
        self.client_repo = ClientRepository(db)

    def get_profile(self, client_id: int) -> Optional[ClientTaxProfile]:
        if not self.client_repo.get_by_id(client_id):
            raise NotFoundError("Client not found", "CLIENT.NOT_FOUND")
        return self.repo.get_by_client_id(client_id)

    def update_profile(self, client_id: int, **fields) -> ClientTaxProfile:
        if not self.client_repo.get_by_id(client_id):
            raise NotFoundError("Client not found", "CLIENT.NOT_FOUND")
        if "vat_type" in fields and fields["vat_type"] is not None:
            try:
                VatType(fields["vat_type"])
            except ValueError:
                raise AppError(f"Invalid vat_type: {fields['vat_type']}", "CLIENT.INVALID_VAT_TYPE", status_code=400)
        return self.repo.upsert(client_id, **fields)
