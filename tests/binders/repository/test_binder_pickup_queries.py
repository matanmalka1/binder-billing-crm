from datetime import date, timedelta

from app.binders.models.binder import BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.utils.time_utils import utcnow
from tests.helpers.identity import seed_client_identity


def _user(test_db):
    user = User(
        full_name="Pickup Query User",
        email="pickup.query@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.flush()
    return user


def _binder(repo, client_id: int, user_id: int, number: str, days_waiting: int, status):
    binder = repo.create(
        client_record_id=client_id,
        binder_number=number,
        period_start=date(2026, 1, 1),
        created_by=user_id,
    )
    binder.status = status
    binder.ready_for_pickup_at = utcnow() - timedelta(days=days_waiting)
    return binder


def test_list_overdue_pickup_returns_only_old_ready_binders(test_db):
    repo = BinderRepository(test_db)
    user = _user(test_db)
    client = seed_client_identity(test_db, full_name="Pickup Client", id_number="PICK001")
    old_ready = _binder(repo, client.id, user.id, "PICK-1", 40, BinderStatus.READY_FOR_PICKUP)
    _binder(repo, client.id, user.id, "PICK-2", 10, BinderStatus.READY_FOR_PICKUP)
    _binder(repo, client.id, user.id, "PICK-3", 45, BinderStatus.IN_OFFICE)
    deleted = _binder(repo, client.id, user.id, "PICK-4", 50, BinderStatus.READY_FOR_PICKUP)
    deleted.deleted_at = utcnow()
    test_db.commit()

    result = repo.list_overdue_pickup(overdue_days=30, limit=10)

    assert [binder.id for binder in result] == [old_ready.id]
