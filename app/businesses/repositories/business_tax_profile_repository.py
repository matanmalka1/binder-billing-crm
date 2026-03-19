from typing import Optional

from sqlalchemy.orm import Session

from app.businesses.models.business_tax_profile import BusinessTaxProfile
from app.utils.time_utils import utcnow


class BusinessTaxProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_business_id(self, business_id: int) -> Optional[BusinessTaxProfile]:
        return (
            self.db.query(BusinessTaxProfile)
            .filter(BusinessTaxProfile.business_id == business_id)
            .first()
        )

    def upsert(self, business_id: int, **fields) -> BusinessTaxProfile:
        profile = self.get_by_business_id(business_id)
        if profile is None:
            profile = BusinessTaxProfile(business_id=business_id, **fields)
            self.db.add(profile)
        else:
            for key, value in fields.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            profile.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(profile)
        return profile
