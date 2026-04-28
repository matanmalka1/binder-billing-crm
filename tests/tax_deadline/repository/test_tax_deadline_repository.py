from datetime import date, timedelta

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from tests.tax_deadline.factories import create_business


def test_list_pending_due_by_date_filters_completed_deleted_and_window(test_db):
    repo = TaxDeadlineRepository(test_db)
    business = create_business(test_db, name_prefix="Repo Window")
    base = date.today()

    expected_1 = repo.create(
        client_record_id=business.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=base + timedelta(days=2),
    )
    expected_2 = repo.create(
        client_record_id=business.client_id,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
        due_date=base + timedelta(days=4),
    )

    repo.create(client_record_id=business.client_id, deadline_type=DeadlineType.NATIONAL_INSURANCE, due_date=base + timedelta(days=1))
    repo.create(client_record_id=business.client_id, deadline_type=DeadlineType.NATIONAL_INSURANCE, due_date=base + timedelta(days=6))

    completed = repo.create(
        client_record_id=business.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=base + timedelta(days=3),
    )
    repo.update_status(completed.id, TaxDeadlineStatus.COMPLETED)

    deleted = repo.create(
        client_record_id=business.client_id,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        due_date=base + timedelta(days=5),
    )
    assert repo.delete(deleted.id, deleted_by=99) is True

    pending = repo.list_pending_due_by_date(
        from_date=base + timedelta(days=2),
        to_date=base + timedelta(days=5),
    )

    assert [d.id for d in pending] == [expected_1.id, expected_2.id]
    assert all(d.status == TaxDeadlineStatus.PENDING for d in pending)


def test_update_exists_and_delete_paths(test_db):
    repo = TaxDeadlineRepository(test_db)
    business = create_business(test_db, name_prefix="Repo Mutations")

    due_date = date.today() + timedelta(days=10)
    deadline = repo.create(
        client_record_id=business.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=due_date,
    )

    assert repo.exists(business.client_id, DeadlineType.VAT, due_date) is True
    assert repo.exists(business.client_id, DeadlineType.VAT, due_date + timedelta(days=1)) is False

    updated = repo.update(
        deadline.id,
        payment_amount=123.4,
        description="updated",
        deadline_type=DeadlineType.ANNUAL_REPORT,
    )
    assert updated is not None
    assert updated.deadline_type == DeadlineType.ANNUAL_REPORT
    assert float(updated.payment_amount) == 123.4
    assert updated.description == "updated"

    assert repo.update(999999, description="missing") is None
    assert repo.delete(deadline.id, deleted_by=7) is True
    assert repo.delete(999999, deleted_by=7) is False
    assert repo.get_by_id(deadline.id) is None
