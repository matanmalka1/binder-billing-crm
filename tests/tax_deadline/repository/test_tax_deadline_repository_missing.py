from datetime import date, timedelta
from datetime import UTC, datetime

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from tests.tax_deadline.factories import create_business


def test_get_by_id_skips_soft_deleted_and_status_update_sets_completed_at(test_db):
    repo = TaxDeadlineRepository(test_db)
    business = create_business(test_db, name_prefix="Repo Missing")

    item = repo.create(
        client_record_id=business.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=5),
    )

    completed = repo.update_status(item.id, TaxDeadlineStatus.COMPLETED)
    assert completed is not None
    assert completed.status == TaxDeadlineStatus.COMPLETED

    assert repo.delete(item.id, deleted_by=101) is True
    assert repo.get_by_id(item.id) is None


def test_update_status_with_completed_at_and_update_due_date(test_db):
    repo = TaxDeadlineRepository(test_db)
    business = create_business(test_db, name_prefix="Repo Edge")

    item = repo.create(
        client_record_id=business.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=2),
    )

    completed_at = datetime.now(UTC).replace(tzinfo=None)
    completed = repo.update_status(item.id, TaxDeadlineStatus.COMPLETED, completed_at=completed_at)
    assert completed is not None
    assert completed.completed_at == completed_at

    new_due = date.today() + timedelta(days=30)
    updated = repo.update(item.id, due_date=new_due)
    assert updated is not None
    assert updated.due_date == new_due

    assert repo.update_status(999999, TaxDeadlineStatus.COMPLETED) is None
