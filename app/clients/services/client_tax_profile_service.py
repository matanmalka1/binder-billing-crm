from typing import Optional

from sqlalchemy.orm import Session

from app.models.client_tax_profile import ClientTaxProfile
from app.clients.repositories.client_repository import ClientRepository
from app.repositories.client_tax_profile_repository import ClientTaxProfileRepository


class ClientTaxProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ClientTaxProfileRepository(db)
        self.client_repo = ClientRepository(db)

    def get_profile(self, client_id: int) -> Optional[ClientTaxProfile]:
        return self.repo.get_by_client_id(client_id)

    def update_profile(self, client_id: int, **fields) -> ClientTaxProfile:
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")
        return self.repo.upsert(client_id, **fields)
