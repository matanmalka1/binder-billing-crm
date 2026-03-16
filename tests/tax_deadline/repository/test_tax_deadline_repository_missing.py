from datetime import date, timedelta

from app.clients.models import Client, ClientType
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


def _client(db, suffix: str) -> Client:
    c = Client(
        full_name=f"Tax Repo Missing {suffix}",
        id_number=f"TDM-{suffix}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_tax_deadline_repository_list_overdue_and_list_by_client(test_db):
    repo = TaxDeadlineRepository(test_db)
    c1 = _client(test_db, "A")
    c2 = _client(test_db, "B")

    overdue = repo.create(
        client_id=c1.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() - timedelta(days=1),
    )
    repo.create(
        client_id=c1.id,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
        due_date=date.today() + timedelta(days=10),
    )
    repo.create(
        client_id=c2.id,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        due_date=date.today() - timedelta(days=2),
    )

    overdue_items = repo.list_overdue(reference_date=date.today())
    assert overdue.id in {d.id for d in overdue_items}

    client_items = repo.list_by_client(client_id=c1.id)
    assert len(client_items) == 2
    assert {d.client_id for d in client_items} == {c1.id}
