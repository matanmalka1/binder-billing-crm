from typing import Optional

from sqlalchemy.orm import Session

from app.models.client_tax_profile import ClientTaxProfile
from app.utils.time import utcnow


class ClientTaxProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_client_id(self, client_id: int) -> Optional[ClientTaxProfile]:
        return (
            self.db.query(ClientTaxProfile)
            .filter(ClientTaxProfile.client_id == client_id)
            .first()
        )

    def upsert(self, client_id: int, **fields) -> ClientTaxProfile:
        profile = self.get_by_client_id(client_id)
        if profile is None:
            profile = ClientTaxProfile(client_id=client_id, **fields)
            self.db.add(profile)
        else:
            for key, value in fields.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            profile.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(profile)
        return profile
