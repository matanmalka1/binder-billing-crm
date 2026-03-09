from datetime import date
from itertools import count

from app.binders.models.binder import BinderType
from app.binders.repositories.binder_repository import BinderRepository
from app.clients.models import Client, ClientType
from app.timeline.repositories.timeline_repository import TimelineRepository
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


_client_seq = count(1)


def _client(db) -> Client:
    idx = next(_client_seq)
    c = Client(
        full_name=f"Timeline Repo Client {idx}",
        id_number=f"TLR{idx:03d}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _user(test_db) -> User:
    user = User(
        full_name="Timeline Repo User",
        email="timeline.repo@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def test_list_client_binders_returns_only_requested_client_binders(test_db):
    user = _user(test_db)
    client_a = _client(test_db)
    client_b = _client(test_db)

    binder_repo = BinderRepository(test_db)
    b1 = binder_repo.create(
        client_id=client_a.id,
        binder_number="TL-B-001",
        binder_type=BinderType.VAT,
        received_at=date.today(),
        received_by=user.id,
    )
    b2 = binder_repo.create(
        client_id=client_a.id,
        binder_number="TL-B-002",
        binder_type=BinderType.ANNUAL_REPORT,
        received_at=date.today(),
        received_by=user.id,
    )
    binder_repo.create(
        client_id=client_b.id,
        binder_number="TL-B-003",
        binder_type=BinderType.SALARY,
        received_at=date.today(),
        received_by=user.id,
    )

    timeline_repo = TimelineRepository(test_db)
    result = timeline_repo.list_client_binders(client_a.id)

    assert {binder.id for binder in result} == {b1.id, b2.id}

