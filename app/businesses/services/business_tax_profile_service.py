from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, NotFoundError
from app.businesses.models.business_tax_profile import BusinessTaxProfile, VatType
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.repositories.business_tax_profile_repository import BusinessTaxProfileRepository


class BusinessTaxProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BusinessTaxProfileRepository(db)
        self.business_repo = BusinessRepository(db)

    def get_profile(self, business_id: int) -> Optional[BusinessTaxProfile]:
        if not self.business_repo.get_by_id(business_id):
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        return self.repo.get_by_business_id(business_id)

    def update_profile(self, business_id: int, **fields) -> BusinessTaxProfile:
        if not self.business_repo.get_by_id(business_id):
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        if "vat_type" in fields and fields["vat_type"] is not None:
            try:
                VatType(fields["vat_type"])
            except ValueError:
                raise AppError(
                    f"סוג מע\"מ לא חוקי: {fields['vat_type']}",
                    "BUSINESS.INVALID_VAT_TYPE",
                    status_code=400,
                )
        return self.repo.upsert(business_id, **fields)
