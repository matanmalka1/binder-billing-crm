from datetime import date
from itertools import count

from app.binders.models.binder import BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.binders.repositories.binder_repository_extensions import BinderRepositoryExtensions
from app.clients.models import Client
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


_client_seq = count(1)


def _user(test_db) -> User:
    user = User(
        full_name="Binder Extensions User",
        email="binder.ext.repo@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _client(db) -> Client:
    idx = next(_client_seq)
    c = Client(
        full_name=f"Binder Extensions Client {idx}",
        id_number=f"BER{idx:03d}",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_open_and_client_queries(test_db):
    user = _user(test_db)
    client_a = _client(test_db)
    client_b = _client(test_db)
    base_repo = BinderRepository(test_db)
    ext_repo = BinderRepositoryExtensions(test_db)

    old = base_repo.create(
        client_id=client_a.id,
        binder_number="BER-001",
        period_start=date(2026, 1, 1),
        created_by=user.id,
    )
    newer = base_repo.create(
        client_id=client_a.id,
        binder_number="BER-002",
        period_start=date(2026, 2, 1),
        created_by=user.id,
    )
    returned = base_repo.create(
        client_id=client_a.id,
        binder_number="BER-003",
        period_start=date(2026, 3, 1),
        created_by=user.id,
    )
    latest_other_client = base_repo.create(
        client_id=client_b.id,
        binder_number="BER-004",
        period_start=date(2026, 4, 1),
        created_by=user.id,
    )

    base_repo.update_status(returned.id, BinderStatus.RETURNED)

    open_binders = ext_repo.list_open_binders(page=1, page_size=20)
    assert [b.id for b in open_binders] == [latest_other_client.id, newer.id, old.id]
    assert ext_repo.count_open_binders() == 3

    by_client = ext_repo.list_by_client(client_a.id, page=1, page_size=20)
    assert [b.id for b in by_client] == [returned.id, newer.id, old.id]
    assert ext_repo.count_by_client(client_a.id) == 3
