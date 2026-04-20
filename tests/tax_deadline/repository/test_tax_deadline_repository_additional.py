from datetime import date, timedelta

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from tests.tax_deadline.factories import create_business


def test_list_by_business_ids_and_filters(test_db):
    repo = TaxDeadlineRepository(test_db)
    business_a = create_business(test_db, name_prefix="Repo A")
    business_b = create_business(test_db, name_prefix="Repo B")

    a_vat = repo.create(
        client_id=business_a.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=1),
    )
    b_vat = repo.create(
        client_id=business_b.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=2),
    )
    b_other = repo.create(
        client_id=business_b.client_id,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
        due_date=date.today() + timedelta(days=3),
    )
    repo.update_status(b_other.id, TaxDeadlineStatus.COMPLETED)

    all_items = repo.list_by_client_ids([business_a.client_id, business_b.client_id])
    assert {d.id for d in all_items} == {a_vat.id, b_vat.id, b_other.id}

    filtered = repo.list_by_client_ids(
        [business_a.client_id, business_b.client_id],
        status=TaxDeadlineStatus.COMPLETED.value,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
    )
    assert [d.id for d in filtered] == [b_other.id]


def test_list_overdue_and_list_by_business(test_db):
    repo = TaxDeadlineRepository(test_db)
    business = create_business(test_db, name_prefix="Repo Overdue")

    overdue = repo.create(
        client_id=business.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() - timedelta(days=1),
    )
    upcoming = repo.create(
        client_id=business.client_id,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
        due_date=date.today() + timedelta(days=10),
    )

    overdue_items = repo.list_overdue(reference_date=date.today())
    assert [d.id for d in overdue_items] == [overdue.id]

    by_client = repo.list_by_client(business.client_id)
    assert {d.id for d in by_client} == {overdue.id, upcoming.id}

    filtered = repo.list_by_client(
        business.client_id,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
    )
    assert [d.id for d in filtered] == [upcoming.id]
