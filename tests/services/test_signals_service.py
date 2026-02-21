from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.clients.models.client import Client, ClientType
from app.binders.services.signals_service import SignalsService, SignalType


def test_overdue_signal(test_db):
    """Test overdue signal computation."""
    client = Client(
        full_name="Signal Test",
        id_number="SIG001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    
    binder = Binder(
        client_id=client.id,
        binder_number="SIG-OVER",
        binder_type=BinderType.OTHER,
        received_at=date.today() - timedelta(days=100),
        expected_return_at=date.today() - timedelta(days=10),
        status=BinderStatus.IN_OFFICE,
        received_by=1,
    )
    test_db.add(binder)
    test_db.commit()
    
    service = SignalsService(test_db)
    signals = service.compute_binder_signals(binder)
    
    assert SignalType.OVERDUE.value in signals


def test_near_sla_signal(test_db):
    """Test near SLA signal computation."""
    client = Client(
        full_name="Signal Test",
        id_number="SIG002",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    
    binder = Binder(
        client_id=client.id,
        binder_number="SIG-NEAR",
        binder_type=BinderType.OTHER,
        received_at=date.today() - timedelta(days=80),
        expected_return_at=date.today() + timedelta(days=10),
        status=BinderStatus.IN_OFFICE,
        received_by=1,
    )
    test_db.add(binder)
    test_db.commit()
    
    service = SignalsService(test_db)
    signals = service.compute_binder_signals(binder)
    
    assert SignalType.NEAR_SLA.value in signals


def test_idle_signal(test_db):
    """Test idle binder signal computation."""
    client = Client(
        full_name="Signal Test",
        id_number="SIG003",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(client)
    test_db.commit()
    
    binder = Binder(
        client_id=client.id,
        binder_number="SIG-IDLE",
        binder_type=BinderType.OTHER,
        received_at=date.today() - timedelta(days=30),
        expected_return_at=date.today() + timedelta(days=60),
        status=BinderStatus.IN_OFFICE,
        received_by=1,
    )
    test_db.add(binder)
    test_db.commit()
    
    service = SignalsService(test_db)
    signals = service.compute_binder_signals(binder)
    
    assert SignalType.IDLE_BINDER.value in signals
