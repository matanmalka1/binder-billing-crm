from datetime import date, timedelta

from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.grouped_deadline_repository import GroupedDeadlineRepository
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from tests.tax_deadline.factories import create_business


def _seed_deadlines(test_db):
    business = create_business(test_db, name_prefix="Grouped Repo")
    write_repo = TaxDeadlineRepository(test_db)
    base = date.today()
    deadlines = [
        write_repo.create(
            client_record_id=business.client_id,
            deadline_type=DeadlineType.VAT,
            due_date=base - timedelta(days=30),
        ),
        write_repo.create(
            client_record_id=business.client_id,
            deadline_type=DeadlineType.ADVANCE_PAYMENT,
            due_date=base + timedelta(days=10),
        ),
        write_repo.create(
            client_record_id=business.client_id,
            deadline_type=DeadlineType.NATIONAL_INSURANCE,
            due_date=base + timedelta(days=130),
        ),
    ]
    test_db.flush()
    return base, deadlines


def _ids(items):
    return [item.id for item in items]


def test_fetch_for_grouping_filters_between_due_from_and_due_to(test_db):
    base, deadlines = _seed_deadlines(test_db)
    repo = GroupedDeadlineRepository(test_db)

    items = repo.fetch_for_grouping(
        due_from=base,
        due_to=base + timedelta(days=90),
    )

    assert _ids(items) == [deadlines[1].id]


def test_fetch_for_grouping_without_dates_does_not_apply_default_window(test_db):
    _base, deadlines = _seed_deadlines(test_db)
    repo = GroupedDeadlineRepository(test_db)

    items = repo.fetch_for_grouping()

    assert _ids(items) == [deadlines[0].id, deadlines[1].id, deadlines[2].id]


def test_fetch_for_grouping_with_only_due_from_filters_forward(test_db):
    base, deadlines = _seed_deadlines(test_db)
    repo = GroupedDeadlineRepository(test_db)

    items = repo.fetch_for_grouping(due_from=base)

    assert _ids(items) == [deadlines[1].id, deadlines[2].id]


def test_fetch_for_grouping_with_only_due_to_filters_until_date(test_db):
    base, deadlines = _seed_deadlines(test_db)
    repo = GroupedDeadlineRepository(test_db)

    items = repo.fetch_for_grouping(due_to=base + timedelta(days=90))

    assert _ids(items) == [deadlines[0].id, deadlines[1].id]
