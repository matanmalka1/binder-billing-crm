from datetime import date

import pytest

from app.charge.models.charge import ChargeStatus
from app.charge.services.billing_service import BillingService
from app.clients.models import Client, ClientType
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.users.models.user import UserRole


def _client(test_db):
    c = Client(
        full_name="Billing Extra Client",
        id_number="BSE001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


def test_billing_service_validation_and_not_found_paths(test_db):
    c = _client(test_db)
    service = BillingService(test_db)

    with pytest.raises(AppError):
        service.create_charge(client_id=c.id, amount=0, charge_type="one_time")

    with pytest.raises(NotFoundError):
        service.mark_charge_paid(999999)
    with pytest.raises(NotFoundError):
        service.cancel_charge(999999)
    with pytest.raises(NotFoundError):
        service.delete_charge(999999)


def test_billing_service_cancel_and_delete_status_guards(test_db):
    c = _client(test_db)
    service = BillingService(test_db)
    charge = service.create_charge(client_id=c.id, amount=50, charge_type="one_time")

    service.issue_charge(charge.id)
    with pytest.raises(AppError):
        service.delete_charge(charge.id)

    canceled = service.cancel_charge(charge.id)
    assert canceled.status == ChargeStatus.CANCELED
    with pytest.raises(ConflictError):
        service.cancel_charge(charge.id)


def test_list_charges_for_role_secretary_hides_amount(test_db):
    c = _client(test_db)
    service = BillingService(test_db)
    service.create_charge(client_id=c.id, amount=77, charge_type="one_time")

    sec = service.list_charges_for_role(UserRole.SECRETARY, page=1, page_size=10)
    adv = service.list_charges_for_role(UserRole.ADVISOR, page=1, page_size=10)
    assert sec.items
    assert adv.items
    assert not hasattr(sec.items[0], "amount")
    assert hasattr(adv.items[0], "amount")
