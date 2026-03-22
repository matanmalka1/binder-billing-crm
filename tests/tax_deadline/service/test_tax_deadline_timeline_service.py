from datetime import date, timedelta

import pytest

from app.businesses.repositories.business_repository import BusinessRepository
from app.core.exceptions import NotFoundError
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository
from app.tax_deadline.services.timeline_service import build_timeline
from tests.tax_deadline.factories import create_business


def test_build_timeline_sorts_and_computes_fields(test_db):
    business = create_business(test_db, name_prefix="Timeline")
    deadline_repo = TaxDeadlineRepository(test_db)

    later = deadline_repo.create(
        business_id=business.id,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        due_date=date.today() + timedelta(days=20),
    )
    sooner = deadline_repo.create(
        business_id=business.id,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
        due_date=date.today() + timedelta(days=4),
    )

    items = build_timeline(
        business.id,
        business_repo=BusinessRepository(test_db),
        deadline_repo=deadline_repo,
    )

    assert [i["id"] for i in items] == [sooner.id, later.id]
    assert items[0]["milestone_label"] == "תשלום מקדמה"
    assert items[1]["milestone_label"] == "הגשת דוח שנתי"
    assert isinstance(items[0]["days_remaining"], int)


def test_build_timeline_raises_when_business_missing(test_db):
    with pytest.raises(NotFoundError):
        build_timeline(
            999999,
            business_repo=BusinessRepository(test_db),
            deadline_repo=TaxDeadlineRepository(test_db),
        )
