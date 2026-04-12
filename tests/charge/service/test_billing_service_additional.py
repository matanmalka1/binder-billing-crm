from datetime import date

import pytest

from app.businesses.models.business import Business, BusinessStatus, EntityType
from app.charge.models.charge import ChargeStatus, ChargeType
from app.charge.services.billing_service import BillingService
from app.charge.services.charge_query_service import ChargeQueryService
from app.clients.models.client import Client
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.users.models.user import UserRole


def _business(test_db, *, status: BusinessStatus = BusinessStatus.ACTIVE):
    client = Client(full_name="Billing Extra Client", id_number=f"BSE{status.value}")
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        entity_type=EntityType.COMPANY_LTD,
        status=status,
        opened_at=date.today(),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


def test_billing_service_validation_and_not_found_paths(test_db):
    business = _business(test_db)
    service = BillingService(test_db)

    with pytest.raises(AppError) as amount_exc:
        service.create_charge(business_id=business.id, amount=0, charge_type=ChargeType.OTHER)
    assert amount_exc.value.code == "CHARGE.AMOUNT_INVALID"

    with pytest.raises(NotFoundError):
        service.create_charge(business_id=999999, amount=10, charge_type=ChargeType.OTHER)

    with pytest.raises(NotFoundError):
        service.mark_charge_paid(999999)
    with pytest.raises(NotFoundError):
        service.cancel_charge(999999)
    with pytest.raises(NotFoundError):
        service.delete_charge(999999)


def test_billing_service_cancel_and_delete_status_guards(test_db):
    business = _business(test_db)
    service = BillingService(test_db)
    charge = service.create_charge(
        business_id=business.id,
        amount=50,
        charge_type=ChargeType.CONSULTATION_FEE,
    )

    service.issue_charge(charge.id)
    with pytest.raises(AppError):
        service.delete_charge(charge.id)

    canceled = service.cancel_charge(charge.id)
    assert canceled.status == ChargeStatus.CANCELED
    with pytest.raises(ConflictError):
        service.cancel_charge(charge.id)


def test_create_charge_blocked_for_closed_and_frozen_business(test_db):
    service = BillingService(test_db)
    closed = _business(test_db, status=BusinessStatus.CLOSED)
    frozen = _business(test_db, status=BusinessStatus.FROZEN)

    with pytest.raises(ForbiddenError) as closed_exc:
        service.create_charge(
            business_id=closed.id,
            amount=10,
            charge_type=ChargeType.MONTHLY_RETAINER,
        )
    assert closed_exc.value.code == "BUSINESS.CLOSED"

    with pytest.raises(ForbiddenError) as frozen_exc:
        service.create_charge(
            business_id=frozen.id,
            amount=10,
            charge_type=ChargeType.MONTHLY_RETAINER,
        )
    assert frozen_exc.value.code == "BUSINESS.FROZEN"


def test_list_charges_for_role_secretary_hides_amount(test_db):
    business = _business(test_db)
    BillingService(test_db).create_charge(
        business_id=business.id,
        amount=77,
        charge_type=ChargeType.CONSULTATION_FEE,
    )

    query = ChargeQueryService(test_db)
    sec = query.list_charges_for_role(UserRole.SECRETARY, page=1, page_size=10)
    adv = query.list_charges_for_role(UserRole.ADVISOR, page=1, page_size=10)
    assert sec.items
    assert adv.items
    assert not hasattr(sec.items[0], "amount")
    assert hasattr(adv.items[0], "amount")
