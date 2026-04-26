from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from tests.tax_deadline.factories import create_business


def test_tax_deadline_repr_contains_core_fields():
    deadline = TaxDeadline(
        id=77,
        client_record_id=15,
        deadline_type=DeadlineType.VAT,
        due_date=date(2026, 1, 19),
    )

    rendered = repr(deadline)
    assert "id=77" in rendered
    assert "client_record_id=15" in rendered
    assert "2026-01-19" in rendered


def test_active_deadline_identity_is_unique_for_period(test_db):
    repo = TaxDeadlineRepository(test_db)
    business = create_business(test_db, name_prefix="Deadline Unique Period")

    repo.create(
        client_record_id=business.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=date(2026, 2, 19),
        period="2026-01",
    )

    with pytest.raises(IntegrityError):
        repo.create(
            client_record_id=business.client_id,
            deadline_type=DeadlineType.VAT,
            due_date=date(2026, 2, 20),
            period="2026-01",
        )

