from datetime import date, timedelta
from itertools import count

from app.clients.models import Client, ClientType
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService


_client_seq = count(1)


def _client(db) -> Client:
    idx = next(_client_seq)
    client = Client(
        full_name=f"Tax Service Client {idx}",
        id_number=f"TDS{idx:03d}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def test_get_client_deadlines_with_status_and_type_filters(test_db):
    client_a = _client(test_db)
    client_b = _client(test_db)
    repo = TaxDeadlineRepository(test_db)
    service = TaxDeadlineService(test_db)
    today = date.today()

    pending_vat = repo.create(
        client_id=client_a.id,
        deadline_type=DeadlineType.VAT,
        due_date=today + timedelta(days=1),
    )
    completed_vat = repo.create(
        client_id=client_a.id,
        deadline_type=DeadlineType.VAT,
        due_date=today + timedelta(days=2),
    )
    repo.update_status(completed_vat.id, TaxDeadlineStatus.COMPLETED)
    annual_report = repo.create(
        client_id=client_a.id,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        due_date=today + timedelta(days=3),
    )
    repo.create(
        client_id=client_b.id,
        deadline_type=DeadlineType.VAT,
        due_date=today + timedelta(days=4),
    )

    all_for_a = service.get_client_deadlines(client_a.id)
    assert {d.id for d in all_for_a} == {
        pending_vat.id,
        completed_vat.id,
        annual_report.id,
    }

    filtered = service.get_client_deadlines(
        client_id=client_a.id,
        status=TaxDeadlineStatus.COMPLETED.value,
        deadline_type=DeadlineType.VAT,
    )
    assert [d.id for d in filtered] == [completed_vat.id]
