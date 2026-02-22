from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.clients.models.client import Client, ClientType
from app.binders.services.signals_service import SignalsService, SignalType


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
        status=BinderStatus.IN_OFFICE,
        received_by=1,
    )
    test_db.add(binder)
    test_db.commit()

    service = SignalsService(test_db)
    signals = service.compute_binder_signals(binder)

    assert SignalType.IDLE_BINDER.value in signals
