from datetime import date, timedelta

from app.clients.models import Client, ClientType
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


def _client(db, id_number: str) -> Client:
    crm_client = Client(
        full_name="TD Repo Additional",
        id_number=id_number,
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(crm_client)
    db.commit()
    db.refresh(crm_client)
    return crm_client


def test_list_by_client_ids_exists_update_and_delete_paths(test_db):
    a = _client(test_db, "TDRA001")
    b = _client(test_db, "TDRA002")
    repo = TaxDeadlineRepository(test_db)

    da = repo.create(a.id, DeadlineType.VAT, date.today() + timedelta(days=1))
    db = repo.create(b.id, DeadlineType.ADVANCE_PAYMENT, date.today() + timedelta(days=2))

    listed = repo.list_by_client_ids([a.id, b.id])
    assert {d.id for d in listed} == {da.id, db.id}

    assert repo.exists(a.id, DeadlineType.VAT, da.due_date) is True
    assert repo.exists(a.id, DeadlineType.VAT, date.today() + timedelta(days=100)) is False

    updated = repo.update(da.id, payment_amount=123.4, description="updated")
    assert float(updated.payment_amount) == 123.4
    assert updated.description == "updated"

    assert repo.delete(db.id) is True
    assert repo.delete(999999) is False
