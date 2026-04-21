from datetime import date

import pytest

from app.common.enums import VatType
from app.core.exceptions import NotFoundError
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.services.deadline_generator import DeadlineGeneratorService
from tests.tax_deadline.factories import create_business


def _set_vat_profile(test_db, business, vat_type: VatType) -> None:
    business.legal_entity.vat_reporting_frequency = vat_type
    test_db.commit()


def test_generate_vat_deadlines_monthly_creates_12_and_is_idempotent(test_db):
    business = create_business(test_db, name_prefix="Gen Monthly")
    _set_vat_profile(test_db, business, VatType.MONTHLY)

    service = DeadlineGeneratorService(test_db)
    first = service.generate_vat_deadlines(business.client_id, 2027)
    second = service.generate_vat_deadlines(business.client_id, 2027)

    assert len(first) == 12
    assert len(second) == 0
    assert {d.deadline_type for d in first} == {DeadlineType.VAT}


def test_generate_vat_deadlines_bimonthly_creates_6(test_db):
    business = create_business(test_db, name_prefix="Gen Bi")
    _set_vat_profile(test_db, business, VatType.BIMONTHLY)

    created = DeadlineGeneratorService(test_db).generate_vat_deadlines(business.client_id, 2027)

    assert len(created) == 6
    assert all(d.deadline_type == DeadlineType.VAT for d in created)


def test_generate_vat_deadlines_exempt_or_missing_profile_creates_none(test_db):
    exempt_business = create_business(test_db, name_prefix="Gen Exempt")
    _set_vat_profile(test_db, exempt_business, VatType.EXEMPT)

    no_profile_business = create_business(test_db, name_prefix="Gen Missing")

    service = DeadlineGeneratorService(test_db)
    assert service.generate_vat_deadlines(exempt_business.client_id, 2026) == []
    assert service.generate_vat_deadlines(no_profile_business.client_id, 2026) == []


def test_generate_advance_annual_and_all(test_db):
    business = create_business(test_db, name_prefix="Gen All")
    _set_vat_profile(test_db, business, VatType.MONTHLY)

    service = DeadlineGeneratorService(test_db)

    advance_created = service.generate_advance_payment_deadlines(business.client_id, 2027)
    annual_created = service.generate_annual_report_deadline(business.client_id, 2027)
    annual_second = service.generate_annual_report_deadline(business.client_id, 2027)

    assert len(advance_created) == 12
    assert len(annual_created) == 1
    assert annual_second == []

    total_created = service.generate_all(business.client_id, 2028)
    assert total_created == 24  # annual is already deduped once a client annual deadline exists


def test_generate_all_raises_for_missing_business(test_db):
    with pytest.raises(NotFoundError):
        DeadlineGeneratorService(test_db).generate_all(999999, 2026)
