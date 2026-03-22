from datetime import date, timedelta

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus, UrgencyLevel
from app.tax_deadline.services.tax_deadline_query_service import TaxDeadlineQueryService
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService
from tests.tax_deadline.factories import create_business


def test_compute_urgency_cases(test_db):
    business = create_business(test_db, name_prefix="Query Urgency")
    writer = TaxDeadlineService(test_db)
    service = TaxDeadlineQueryService(test_db)
    reference = date.today()

    overdue = writer.create_deadline(business.id, DeadlineType.VAT, reference - timedelta(days=1))
    red = writer.create_deadline(business.id, DeadlineType.ADVANCE_PAYMENT, reference + timedelta(days=2))
    yellow = writer.create_deadline(business.id, DeadlineType.NATIONAL_INSURANCE, reference + timedelta(days=5))
    green = writer.create_deadline(business.id, DeadlineType.ANNUAL_REPORT, reference + timedelta(days=30))

    assert service.compute_urgency(overdue, reference) == UrgencyLevel.OVERDUE
    assert service.compute_urgency(red, reference) == UrgencyLevel.RED
    assert service.compute_urgency(yellow, reference) == UrgencyLevel.YELLOW
    assert service.compute_urgency(green, reference) == UrgencyLevel.GREEN

    writer.mark_completed(red.id)
    completed = writer.get_deadline(red.id)
    assert service.compute_urgency(completed, reference) is None


def test_upcoming_overdue_name_search_and_summary(test_db):
    business = create_business(test_db, name_prefix="Query Search")
    other = create_business(test_db, name_prefix="Not Matching")
    writer = TaxDeadlineService(test_db)
    service = TaxDeadlineQueryService(test_db)
    today = date.today()

    overdue = writer.create_deadline(business.id, DeadlineType.VAT, today - timedelta(days=1))
    red = writer.create_deadline(business.id, DeadlineType.ADVANCE_PAYMENT, today + timedelta(days=1))
    yellow = writer.create_deadline(business.id, DeadlineType.ANNUAL_REPORT, today + timedelta(days=5))
    green = writer.create_deadline(business.id, DeadlineType.OTHER, today + timedelta(days=20))
    other_due = writer.create_deadline(other.id, DeadlineType.OTHER, today + timedelta(days=3))

    upcoming = service.get_upcoming_deadlines(days_ahead=7, reference_date=today)
    assert {d.id for d in upcoming} == {red.id, yellow.id, other_due.id}

    overdue_list = service.get_overdue_deadlines(reference_date=today)
    assert [d.id for d in overdue_list] == [overdue.id]

    by_name = service.get_deadlines_by_client_name("Query Search")
    assert {d.id for d in by_name} == {overdue.id, red.id, yellow.id, green.id}

    assert service.get_deadlines_by_client_name("no-match") == []

    name_map = service.build_business_name_map([overdue, red])
    assert name_map[business.id].startswith("Query Search")

    summary = service.get_urgent_deadlines_summary(reference_date=today)
    urgent_ids = {item["deadline"].id for item in summary["urgent"]}
    assert urgent_ids == {overdue.id, red.id, yellow.id, other_due.id}
    assert {d.id for d in summary["upcoming"]} == {red.id, yellow.id, other_due.id}
