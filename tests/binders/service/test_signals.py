from datetime import date, timedelta

from app.binders.models.binder import Binder, BinderStatus
from app.clients.models.client import Client
from app.binders.services.signals_service import SignalsService, SignalType


def test_idle_signal(test_db):
    """Test idle binder signal computation."""
    client = Client(
        full_name="Signal Test",
        id_number="SIG003",
    )
    test_db.add(client)
    test_db.commit()

    binder = Binder(
        client_id=client.id,
        binder_number="SIG-IDLE",
        period_start=date.today() - timedelta(days=30),
        status=BinderStatus.IN_OFFICE,
        created_by=1,
    )
    test_db.add(binder)
    test_db.commit()

    service = SignalsService(test_db)
    signals = service.compute_binder_signals(binder)

    assert SignalType.IDLE_BINDER.value in signals
