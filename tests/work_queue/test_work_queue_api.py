from datetime import date, timedelta

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from tests.helpers.task_helpers import create_business
from tests.helpers.tax_calendar_links import create_linked_advance_payment


def test_work_queue_api_returns_advance_payment_payload(client, test_db, advisor_headers):
    biz = create_business(test_db)
    due_date = date.today() - timedelta(days=1)
    payment = create_linked_advance_payment(
        test_db,
        client_record_id=biz.client_id,
        period="2026-02",
        due_date=due_date,
        expected_amount=1000,
        paid_amount=250,
    )
    payment.status = AdvancePaymentStatus.PARTIAL
    test_db.commit()

    response = client.get(
        "/api/v1/work-queue?exclude_source_types=vat_filing"
        "&exclude_source_types=annual_report",
        headers=advisor_headers,
    )

    assert response.status_code == 200
    item = next(i for i in response.json() if i["source_type"] == "advance_payment")
    assert "item_type" not in item
    assert item["payload"]["period"] == "2026-02"
    assert item["payload"]["remaining_amount"] == "750.00"


def test_tasks_unified_route_removed(client, advisor_headers):
    response = client.get("/api/v1/tasks/unified", headers=advisor_headers)

    assert response.status_code == 404
