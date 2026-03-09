from datetime import date
from decimal import Decimal

from app.charge.models.charge import ChargeStatus, ChargeType
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.models.client import Client, ClientType
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def _user(test_db):
    user = User(
        full_name="Charge Admin",
        email="charge.admin@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _client(test_db, name: str, id_number: str):
    client = Client(
        full_name=name,
        id_number=id_number,
        client_type=ClientType.COMPANY,
        opened_at=date(2024, 1, 1),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_list_count_and_soft_delete(test_db):
    repo = ChargeRepository(test_db)
    user = _user(test_db)
    client = _client(test_db, "Charge Client", "CH001")
    other_client = _client(test_db, "Other Client", "CH002")

    draft = repo.create(
        client_id=client.id,
        amount=Decimal("100.00"),
        charge_type=ChargeType.RETAINER,
        created_by=user.id,
    )
    paid = repo.create(
        client_id=client.id,
        amount=Decimal("200.00"),
        charge_type=ChargeType.ONE_TIME,
        created_by=user.id,
    )
    repo.update_status(paid.id, ChargeStatus.PAID)

    other = repo.create(
        client_id=other_client.id,
        amount=Decimal("50.00"),
        charge_type=ChargeType.RETAINER,
        created_by=user.id,
    )
    repo.update_status(other.id, ChargeStatus.ISSUED)

    assert repo.count_charges(client_id=client.id) == 2
    assert repo.count_charges(status=ChargeStatus.PAID) == 1

    client_charges = repo.list_charges(client_id=client.id)
    assert {c.id for c in client_charges} == {draft.id, paid.id}

    paid_list = repo.list_charges(status=ChargeStatus.PAID)
    assert [c.id for c in paid_list] == [paid.id]

    deleted = repo.soft_delete(draft.id, deleted_by=user.id)
    assert deleted is True
    assert {c.id for c in repo.list_charges(client_id=client.id)} == {paid.id}
    assert repo.count_charges(client_id=client.id) == 1
