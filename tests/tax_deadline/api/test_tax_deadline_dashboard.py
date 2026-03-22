from datetime import date, timedelta
from decimal import Decimal

from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline
from tests.tax_deadline.factories import create_business


def _seed_deadlines(db):
    today = date.today()
    business_a = create_business(db, name_prefix="Dash A")
    business_b = create_business(db, name_prefix="Dash B")
    business_c = create_business(db, name_prefix="Dash C")

    deadlines = [
        TaxDeadline(
            business_id=business_a.id,
            deadline_type=DeadlineType.VAT,
            due_date=today - timedelta(days=1),
            payment_amount=Decimal("100.00"),
        ),
        TaxDeadline(
            business_id=business_b.id,
            deadline_type=DeadlineType.ANNUAL_REPORT,
            due_date=today + timedelta(days=1),
            payment_amount=Decimal("200.00"),
        ),
        TaxDeadline(
            business_id=business_c.id,
            deadline_type=DeadlineType.ADVANCE_PAYMENT,
            due_date=today + timedelta(days=5),
            payment_amount=Decimal("300.00"),
        ),
        TaxDeadline(
            business_id=business_c.id,
            deadline_type=DeadlineType.OTHER,
            due_date=today + timedelta(days=10),
            payment_amount=Decimal("400.00"),
        ),
    ]
    db.add_all(deadlines)
    db.commit()


def test_dashboard_urgent_deadlines(client, test_db, advisor_headers):
    _seed_deadlines(test_db)

    resp = client.get("/api/v1/tax-deadlines/dashboard/urgent", headers=advisor_headers)
    assert resp.status_code == 200
    data = resp.json()

    urgent = data["urgent"]
    urgencies = {item["urgency"] for item in urgent}
    assert {"overdue", "red", "yellow"} == urgencies

    amount_map = {item["urgency"]: item["payment_amount"] for item in urgent}
    assert float(amount_map["overdue"]) == 100.0
    assert float(amount_map["red"]) == 200.0
    assert float(amount_map["yellow"]) == 300.0

    upcoming = data["upcoming"]
    assert len(upcoming) == 2
    today = date.today()
    assert {item["due_date"] for item in upcoming} == {
        (today + timedelta(days=1)).isoformat(),
        (today + timedelta(days=5)).isoformat(),
    }
