from datetime import date, datetime, timedelta
from itertools import count

from app.clients.models import Client, ClientType
from app.correspondence.models.correspondence import CorrespondenceType
from app.correspondence.repositories.correspondence_repository import CorrespondenceRepository
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


_client_seq = count(1)


def _client(db) -> Client:
    idx = next(_client_seq)
    c = Client(
        full_name=f"Correspondence Repo Client {idx}",
        id_number=f"CRP{idx:03d}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _user(test_db) -> User:
    user = User(
        full_name="Correspondence Repo User",
        email="correspondence.repo@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def test_list_by_client_paginated_and_soft_delete(test_db):
    repo = CorrespondenceRepository(test_db)
    user = _user(test_db)
    client_a = _client(test_db)
    client_b = _client(test_db)
    base = datetime(2026, 1, 1, 12, 0, 0)

    first = repo.create(
        client_id=client_a.id,
        correspondence_type=CorrespondenceType.EMAIL,
        subject="First",
        occurred_at=base + timedelta(days=1),
        created_by=user.id,
    )
    second = repo.create(
        client_id=client_a.id,
        correspondence_type=CorrespondenceType.CALL,
        subject="Second",
        occurred_at=base + timedelta(days=2),
        created_by=user.id,
    )
    third = repo.create(
        client_id=client_a.id,
        correspondence_type=CorrespondenceType.MEETING,
        subject="Third",
        occurred_at=base + timedelta(days=3),
        created_by=user.id,
    )
    repo.create(
        client_id=client_b.id,
        correspondence_type=CorrespondenceType.LETTER,
        subject="Other client",
        occurred_at=base + timedelta(days=4),
        created_by=user.id,
    )

    page_1_items, page_1_total = repo.list_by_client_paginated(client_a.id, page=1, page_size=2)
    assert page_1_total == 3
    assert [entry.id for entry in page_1_items] == [third.id, second.id]

    page_2_items, page_2_total = repo.list_by_client_paginated(client_a.id, page=2, page_size=2)
    assert page_2_total == 3
    assert [entry.id for entry in page_2_items] == [first.id]

    assert repo.soft_delete(second.id, deleted_by=user.id) is True
    assert repo.get_by_id(second.id) is None

    remaining, total_after_delete = repo.list_by_client_paginated(client_a.id, page=1, page_size=10)
    assert total_after_delete == 2
    assert {entry.id for entry in remaining} == {first.id, third.id}
    assert repo.soft_delete(999999, deleted_by=user.id) is False

