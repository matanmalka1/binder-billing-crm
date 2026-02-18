from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus
from app.clients.models.client import Client, ClientType
from app.binders.services.operational_signals_service import OperationalSignalsService


def test_operational_signals_missing_documents(test_db):
    """Test operational signals report missing documents."""
    client = Client(
        full_name="Signals Test Client",
        id_number="888888888",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    service = OperationalSignalsService(test_db)
    signals = service.get_client_signals(client.id)

    assert signals["client_id"] == client.id
    assert len(signals["missing_documents"]) == 3


def test_operational_signals_binders_nearing_sla(test_db, test_user):
    """Test operational signals detect binders nearing SLA."""
    client = Client(
        full_name="SLA Test Client",
        id_number="999999999",
        client_type=ClientType.OSEK_MURSHE,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    # Create binder nearing SLA (14 days remaining)
    binder = Binder(
        client_id=client.id,
        binder_number="BND-NEAR-1",
        received_at=date.today() - timedelta(days=76),
        expected_return_at=date.today() + timedelta(days=14),
        status=BinderStatus.IN_OFFICE,
        received_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()

    service = OperationalSignalsService(test_db)
    signals = service.get_client_signals(client.id, reference_date=date.today())

    assert len(signals["binders_nearing_sla"]) == 1
    assert signals["binders_nearing_sla"][0]["binder_id"] == binder.id


def test_operational_signals_overdue_binders(test_db, test_user):
    """Test operational signals detect overdue binders."""
    client = Client(
        full_name="Overdue Test Client",
        id_number="000000001",
        client_type=ClientType.EMPLOYEE,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    # Create overdue binder
    binder = Binder(
        client_id=client.id,
        binder_number="BND-OVER-1",
        received_at=date.today() - timedelta(days=100),
        expected_return_at=date.today() - timedelta(days=10),
        status=BinderStatus.IN_OFFICE,
        received_by=test_user.id,
    )
    test_db.add(binder)
    test_db.commit()

    service = OperationalSignalsService(test_db)
    signals = service.get_client_signals(client.id, reference_date=date.today())

    assert len(signals["binders_overdue"]) == 1
    assert signals["binders_overdue"][0]["binder_id"] == binder.id
    assert signals["binders_overdue"][0]["days_overdue"] == 10
