from datetime import date

from app.clients.models.client import Client, ClientType
from app.binders.services.signals_service import SignalsService


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

    service = SignalsService(test_db)
    signals = service.compute_client_operational_signals(client.id)

    assert signals["client_id"] == client.id
    assert len(signals["missing_documents"]) == 3
