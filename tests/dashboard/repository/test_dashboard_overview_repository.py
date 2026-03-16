from datetime import date

from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.binders.repositories.binder_repository import BinderRepository
from app.clients.models.client import Client, ClientType
from app.clients.repositories.client_repository import ClientRepository
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def test_get_overview_metrics_counts_clients_and_active_binders(test_db):
    user = User(
        full_name="Receiver",
        email="receiver@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)

    client_a = Client(
        full_name="Alpha Ltd",
        id_number="C001",
        client_type=ClientType.COMPANY,
        opened_at=date(2024, 1, 1),
    )
    client_b = Client(
        full_name="Beta LLC",
        id_number="C002",
        client_type=ClientType.COMPANY,
        opened_at=date(2024, 2, 1),
    )
    test_db.add_all([client_a, client_b])
    test_db.commit()

    binder_active = Binder(
        client_id=client_a.id,
        binder_number="B-1",
        binder_type=BinderType.VAT,
        received_at=date(2024, 3, 1),
        status=BinderStatus.IN_OFFICE,
        received_by=user.id,
    )
    binder_returned = Binder(
        client_id=client_b.id,
        binder_number="B-2",
        binder_type=BinderType.VAT,
        received_at=date(2024, 3, 2),
        returned_at=date(2024, 3, 5),
        status=BinderStatus.RETURNED,
        received_by=user.id,
        returned_by=user.id,
    )
    test_db.add_all([binder_active, binder_returned])
    test_db.commit()

    total_clients = ClientRepository(test_db).count()
    active_binders = BinderRepository(test_db).count_active()

    assert total_clients >= 2
    assert active_binders >= 1
    # Returned binder should not be counted
    assert active_binders < total_clients + 1
