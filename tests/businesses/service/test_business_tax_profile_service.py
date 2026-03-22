from app.businesses.models.business_tax_profile import VatType
from app.businesses.services.business_tax_profile_service import BusinessTaxProfileService
from app.core.exceptions import AppError, NotFoundError


class _BusinessRepo:
    def __init__(self, business):
        self._business = business

    def get_by_id(self, _business_id):
        return self._business


class _ProfileRepo:
    def __init__(self):
        self.calls = []

    def get_by_business_id(self, business_id):
        self.calls.append(("get", business_id))
        return None

    def upsert(self, business_id, **fields):
        self.calls.append(("upsert", business_id, fields))
        return type("Profile", (), {"business_id": business_id, **fields})()


def test_get_profile_raises_when_business_missing(test_db):
    service = BusinessTaxProfileService(test_db)
    service.business_repo = _BusinessRepo(None)

    try:
        service.get_profile(100)
        raise AssertionError("Expected NotFoundError")
    except NotFoundError as exc:
        assert exc.code == "BUSINESS.NOT_FOUND"


def test_update_profile_rejects_invalid_vat_type(test_db):
    service = BusinessTaxProfileService(test_db)
    service.business_repo = _BusinessRepo(object())
    service.repo = _ProfileRepo()

    try:
        service.update_profile(1, vat_type="invalid")
        raise AssertionError("Expected AppError")
    except AppError as exc:
        assert exc.code == "BUSINESS.INVALID_VAT_TYPE"


def test_update_profile_accepts_valid_vat_type_and_upserts(test_db):
    service = BusinessTaxProfileService(test_db)
    service.business_repo = _BusinessRepo(object())
    fake_repo = _ProfileRepo()
    service.repo = fake_repo

    profile = service.update_profile(7, vat_type=VatType.EXEMPT.value, accountant_name="Dana")

    assert profile.business_id == 7
    assert profile.vat_type == VatType.EXEMPT.value
    assert profile.accountant_name == "Dana"
    assert fake_repo.calls[-1] == (
        "upsert",
        7,
        {"vat_type": VatType.EXEMPT.value, "accountant_name": "Dana"},
    )
