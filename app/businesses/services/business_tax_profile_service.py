import json
from typing import Optional

from sqlalchemy.orm import Session

from app.audit.constants import ACTION_PROFILE_UPDATED, ENTITY_TAX_PROFILE
from app.audit.repositories.entity_audit_log_repository import EntityAuditLogRepository
from app.businesses.models.business_tax_profile import BusinessTaxProfile, VatType
from app.businesses.repositories.business_repository import BusinessRepository
from app.businesses.repositories.business_tax_profile_repository import BusinessTaxProfileRepository
from app.core.exceptions import AppError, NotFoundError


class BusinessTaxProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BusinessTaxProfileRepository(db)
        self.business_repo = BusinessRepository(db)
        self._audit = EntityAuditLogRepository(db)

    def get_profile(self, business_id: int) -> Optional[BusinessTaxProfile]:
        if not self.business_repo.get_by_id(business_id):
            raise NotFoundError(f"עסק {business_id} לא נמצא", "BUSINESS.NOT_FOUND")
        return self.repo.get_by_business_id(business_id)

    def get_profile_or_empty(self, business_id: int):
        """Return the tax profile, or an empty response shell if none exists yet."""
        from app.businesses.schemas.business_tax_profile_schemas import BusinessTaxProfileResponse
        business = self.business_repo.get_by_id(business_id)
        profile = self.repo.get_by_business_id(business_id)
        business_type_key = business.business_type.value if business and business.business_type else None
        client_vat_freq = (
            business.client.vat_reporting_frequency
            if business and business.client
            else None
        )
        if profile is None:
            return BusinessTaxProfileResponse(
                business_id=business_id,
                business_type_key=business_type_key,
                client_vat_reporting_frequency=client_vat_freq,
            )
        response = BusinessTaxProfileResponse.model_validate(profile)
        response.business_type_key = business_type_key
        response.client_vat_reporting_frequency = client_vat_freq
        return response

    def update_profile(self, business_id: int, actor_id: Optional[int] = None, **fields) -> BusinessTaxProfile:
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

        old_profile = self.repo.get_by_business_id(business_id)
        old_snapshot = {k: getattr(old_profile, k, None) for k in fields if old_profile and hasattr(old_profile, k)}
        updated = self.repo.upsert(business_id, **fields)
        new_snapshot = {k: getattr(updated, k, None) for k in fields if hasattr(updated, k)}

        def _serialize(d):
            return {k: v.value if hasattr(v, "value") else str(v) if v is not None else None for k, v in d.items()}

        if actor_id:
            self._audit.append(
                entity_type=ENTITY_TAX_PROFILE,
                entity_id=business_id,
                performed_by=actor_id,
                action=ACTION_PROFILE_UPDATED,
                old_value=json.dumps(_serialize(old_snapshot)) if old_snapshot else None,
                new_value=json.dumps(_serialize(new_snapshot)),
            )
        return updated
