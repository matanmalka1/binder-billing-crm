from datetime import date, timedelta
from decimal import Decimal

from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.binders.services.signals_service import SignalsService, SignalType
from app.charge.models.charge import ChargeStatus, ChargeType
from app.charge.repositories.charge_repository import ChargeRepository
from app.clients.models import Client, ClientType
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService


def _user(test_db) -> User:
    user = User(
        full_name="Signals Client User",
        email="signals.client@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _client(test_db) -> Client:
    client = Client(
        full_name="Signals Client",
        id_number="SCS001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return client


def test_compute_client_signals_includes_documents_unpaid_and_binder_signals(test_db):
    user = _user(test_db)
    client = _client(test_db)

    ready_binder = Binder(
        client_id=client.id,
        binder_number="SCS-READY",
        binder_type=BinderType.OTHER,
        received_at=date.today() - timedelta(days=2),
        status=BinderStatus.READY_FOR_PICKUP,
        received_by=user.id,
    )
    idle_binder = Binder(
        client_id=client.id,
        binder_number="SCS-IDLE",
        binder_type=BinderType.OTHER,
        received_at=date.today() - timedelta(days=40),
        status=BinderStatus.IN_OFFICE,
        received_by=user.id,
    )
    test_db.add_all([ready_binder, idle_binder])
    test_db.commit()

    charge_repo = ChargeRepository(test_db)
    issued = charge_repo.create(
        client_id=client.id,
        amount=Decimal("200.00"),
        charge_type=ChargeType.ONE_TIME,
        created_by=user.id,
    )
    charge_repo.update_status(issued.id, ChargeStatus.ISSUED)

    result = SignalsService(test_db).compute_client_signals(client.id)

    assert set(result["missing_documents"]) == {
        "id_copy",
        "power_of_attorney",
        "engagement_agreement",
    }
    assert result["unpaid_charges"] is True
    assert result["binder_signals"][ready_binder.id] == [SignalType.READY_FOR_PICKUP.value]
    assert result["binder_signals"][idle_binder.id] == [SignalType.IDLE_BINDER.value]

