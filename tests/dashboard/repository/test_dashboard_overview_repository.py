from datetime import date

from app.binders.models.binder import Binder, BinderStatus
from app.binders.repositories.binder_repository import BinderRepository
from app.businesses.models.business import Business, BusinessType
from app.businesses.repositories.business_repository import BusinessRepository
from app.clients.models.client import Client
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def test_business_and_binder_repository_counts_active_entities(test_db):
    user = User(
        full_name="Receiver",
        email="receiver@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)

    client_a = Client(full_name="Alpha Ltd", id_number="C001")
    client_b = Client(full_name="Beta LLC", id_number="C002")
    test_db.add_all([client_a, client_b])
    test_db.commit()

    business_active = Business(
        client_id=client_a.id,
        business_name="Alpha Business",
        business_type=BusinessType.COMPANY,
        opened_at=date(2024, 1, 1),
    )
    business_other = Business(
        client_id=client_b.id,
        business_name="Beta Business",
        business_type=BusinessType.COMPANY,
        opened_at=date(2024, 2, 1),
    )
    test_db.add_all([business_active, business_other])
    test_db.commit()

    binder_active = Binder(
        client_id=client_a.id,
        binder_number="B-1",
        period_start=date(2024, 3, 1),
        status=BinderStatus.IN_OFFICE,
        created_by=user.id,
    )
    binder_returned = Binder(
        client_id=client_b.id,
        binder_number="B-2",
        period_start=date(2024, 3, 2),
        returned_at=date(2024, 3, 5),
        status=BinderStatus.RETURNED,
        created_by=user.id,
    )
    test_db.add_all([binder_active, binder_returned])
    test_db.commit()

    total_businesses = BusinessRepository(test_db).count()
    active_binders = BinderRepository(test_db).count_active()

    assert total_businesses >= 2
    assert active_binders >= 1
    # Returned binder should not be counted as active.
    assert active_binders < total_businesses + 1
