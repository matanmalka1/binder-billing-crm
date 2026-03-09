from datetime import date

from app.clients.models.client import ClientStatus, ClientType
from app.clients.repositories.client_repository import ClientRepository
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def _user(test_db):
    user = User(
        full_name="Client Admin",
        email="client.admin@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def test_client_repository_lookup_and_soft_delete(test_db):
    repo = ClientRepository(test_db)
    user = _user(test_db)

    alpha = repo.create(
        full_name="Alpha Client",
        id_number="CL001",
        client_type=ClientType.COMPANY,
        opened_at=date(2024, 1, 1),
    )
    zeta = repo.create(
        full_name="Zeta Client",
        id_number="CL002",
        client_type=ClientType.COMPANY,
        opened_at=date(2024, 2, 1),
    )

    assert repo.get_by_id_number("CL001").id == alpha.id

    by_ids = repo.list_by_ids([alpha.id, zeta.id])
    assert {c.id for c in by_ids} == {alpha.id, zeta.id}

    all_clients = repo.list_all()
    assert [c.full_name for c in all_clients] == ["Alpha Client", "Zeta Client"]

    deleted = repo.soft_delete(alpha.id, deleted_by=user.id)
    assert deleted is True
    assert repo.get_by_id(alpha.id) is None
    assert [c.id for c in repo.list_all()] == [zeta.id]

    active_only = repo.list_all(status=ClientStatus.ACTIVE)
    assert [c.id for c in active_only] == [zeta.id]
