from datetime import date, timedelta
from itertools import count

from app.clients.models import Client, ClientType
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


_client_seq = count(1)


def _client(db) -> Client:
    idx = next(_client_seq)
    c = Client(
        full_name=f"Tax Deadline Repo Client {idx}",
        id_number=f"TDR{idx:03d}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_list_pending_due_by_date_filters_completed_and_out_of_window(test_db):
    repo = TaxDeadlineRepository(test_db)
    crm_client = _client(test_db)
    base = date.today()
    from_date = base + timedelta(days=2)
    to_date = base + timedelta(days=5)

    expected_1 = repo.create(client_id=crm_client.id, deadline_type=DeadlineType.VAT, due_date=from_date)
    expected_2 = repo.create(client_id=crm_client.id, deadline_type=DeadlineType.ADVANCE_PAYMENT, due_date=base + timedelta(days=4))
    expected_3 = repo.create(client_id=crm_client.id, deadline_type=DeadlineType.ANNUAL_REPORT, due_date=to_date)

    repo.create(client_id=crm_client.id, deadline_type=DeadlineType.OTHER, due_date=base + timedelta(days=1))
    repo.create(client_id=crm_client.id, deadline_type=DeadlineType.OTHER, due_date=base + timedelta(days=6))
    completed = repo.create(client_id=crm_client.id, deadline_type=DeadlineType.VAT, due_date=base + timedelta(days=3))
    repo.update_status(completed.id, TaxDeadlineStatus.COMPLETED, completed_at=base)

    pending = repo.list_pending_due_by_date(from_date=from_date, to_date=to_date)

    assert [d.id for d in pending] == [expected_1.id, expected_2.id, expected_3.id]
    assert all(d.status == TaxDeadlineStatus.PENDING for d in pending)

