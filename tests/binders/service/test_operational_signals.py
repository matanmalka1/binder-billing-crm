from datetime import date

from app.businesses.models.business import Business, BusinessType
from app.clients.models.client import Client
from app.binders.services.signals_service import SignalsService


def test_operational_signals_missing_documents(test_db, test_user):
    """Test operational signals report missing documents."""
    client = Client(
        full_name="Signals Test Client",
        id_number="888888888",
    )
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name="Signals Business",
        business_type=BusinessType.COMPANY,
        opened_at=date.today(),
        created_by=test_user.id,
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)

    service = SignalsService(test_db)
    signals = service.compute_business_operational_signals(business.id)

    assert signals["business_id"] == business.id
    assert len(signals["missing_documents"]) == 3
