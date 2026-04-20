from datetime import date, timedelta

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadlineStatus
from app.tax_deadline.services.tax_deadline_service import TaxDeadlineService
from tests.tax_deadline.factories import create_business


def test_get_business_deadlines_with_status_and_type_filters(test_db):
    business_a = create_business(test_db, name_prefix="Filter A")
    business_b = create_business(test_db, name_prefix="Filter B")
    service = TaxDeadlineService(test_db)
    today = date.today()

    pending_vat = service.create_deadline(
        client_id=business_a.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=today + timedelta(days=1),
    )
    completed_vat = service.create_deadline(
        client_id=business_a.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=today + timedelta(days=2),
    )
    service.mark_completed(completed_vat.id)

    annual_report = service.create_deadline(
        client_id=business_a.client_id,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        due_date=today + timedelta(days=3),
    )
    service.create_deadline(
        client_id=business_b.client_id,
        deadline_type=DeadlineType.VAT,
        due_date=today + timedelta(days=4),
    )

    all_for_a = service.get_client_deadlines(business_a.client_id)
    assert {d.id for d in all_for_a} == {pending_vat.id, completed_vat.id, annual_report.id}

    filtered = service.get_client_deadlines(
        client_id=business_a.client_id,
        status=TaxDeadlineStatus.COMPLETED.value,
        deadline_type=DeadlineType.VAT,
    )
    assert [d.id for d in filtered] == [completed_vat.id]
