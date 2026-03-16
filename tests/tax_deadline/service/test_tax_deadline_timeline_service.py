from datetime import date, timedelta

from app.clients.models import Client, ClientType
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.services.timeline_service import build_timeline


def _client(test_db) -> Client:
    c = Client(
        full_name="Tax Timeline Service Client",
        id_number="TTS-001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


def test_build_timeline_sorts_and_computes_fields(test_db):
    client = _client(test_db)
    repo = TaxDeadlineRepository(test_db)

    later = repo.create(client.id, DeadlineType.ANNUAL_REPORT, date.today() + timedelta(days=20))
    sooner = repo.create(client.id, DeadlineType.VAT, date.today() + timedelta(days=4))

    items = build_timeline(client.id, client_repo=repo, deadline_repo=repo)

    assert [i["id"] for i in items] == [sooner.id, later.id]
    assert items[0]["milestone_label"] in {"vat", "vat_monthly", "vat_bimonthly", "הגשת דוח מע\"מ חודשי", "הגשת דוח מע\"מ דו-חודשי"}
    assert isinstance(items[0]["days_remaining"], int)
