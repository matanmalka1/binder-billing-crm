from datetime import date, timedelta

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.clients.models.client_record import ClientRecord
from tests.helpers.task_helpers import create_business
from tests.helpers.tax_calendar_links import create_linked_advance_payment


def test_work_queue_api_returns_advance_payment_payload(client, test_db, advisor_headers):
    biz = create_business(test_db)
    test_db.get(ClientRecord, biz.client_id).office_client_number = 1
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
    assert item["client_name"].startswith("Task Test Client")
    assert item["client_office_number"] == 1
    assert item["payload"]["period"] == "2026-02"
    assert item["payload"]["period_label"] == "פברואר 2026"
    assert item["payload"]["frequency"] == "monthly"
    assert item["payload"]["remaining_amount"] == "750.00"


def test_tasks_route_exists(client, advisor_headers):
    response = client.get("/api/v1/tasks", headers=advisor_headers)

    assert response.status_code == 200


def test_work_queue_api_pagination(client, test_db, advisor_headers):
    from app.charge.models.charge import Charge, ChargeStatus, ChargeType
    from tests.helpers.task_helpers import create_business

    biz = create_business(test_db)
    for days_ago in [31, 32, 33]:
        test_db.add(
            Charge(
                client_record_id=biz.client_id,
                business_id=biz.id,
                amount=100,
                charge_type=ChargeType.OTHER,
                status=ChargeStatus.ISSUED,
                issued_at=date.today() - timedelta(days=days_ago),
            )
        )
    test_db.commit()

    r1 = client.get(
        f"/api/v1/work-queue?business_id={biz.id}&limit=2&offset=0",
        headers=advisor_headers,
    )
    r2 = client.get(
        f"/api/v1/work-queue?business_id={biz.id}&limit=2&offset=2",
        headers=advisor_headers,
    )

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert len(r1.json()) == 2
    assert len(r2.json()) == 1


def test_work_queue_api_limit_max_enforced(client, advisor_headers):
    response = client.get(
        "/api/v1/work-queue?limit=999",
        headers=advisor_headers,
    )
    assert response.status_code == 422
