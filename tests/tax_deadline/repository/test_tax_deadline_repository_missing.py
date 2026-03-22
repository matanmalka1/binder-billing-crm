from datetime import date, timedelta

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from tests.tax_deadline.factories import create_business


def test_get_by_id_skips_soft_deleted_and_status_update_sets_completed_at(test_db):
    repo = TaxDeadlineRepository(test_db)
    business = create_business(test_db, name_prefix="Repo Missing")

    item = repo.create(
        business_id=business.id,
        deadline_type=DeadlineType.VAT,
        due_date=date.today() + timedelta(days=5),
    )

    completed = repo.update_status(item.id, TaxDeadlineStatus.COMPLETED)
    assert completed is not None
    assert completed.status == TaxDeadlineStatus.COMPLETED

    assert repo.delete(item.id, deleted_by=101) is True
    assert repo.get_by_id(item.id) is None
