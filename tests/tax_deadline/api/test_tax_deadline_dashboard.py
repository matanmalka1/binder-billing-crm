from datetime import date, timedelta
from decimal import Decimal

from app.clients.models import Client, ClientType
from app.tax_deadline.models.tax_deadline import DeadlineType, TaxDeadline, TaxDeadlineStatus


def _seed_deadlines(db):
    today = date.today()
    clients = []
    for idx in range(3):
        c = Client(
            full_name=f"Deadline Client {idx}",
            id_number=f"DLN-{idx}",
            client_type=ClientType.COMPANY,
            opened_at=today,
        )
        db.add(c)
        clients.append(c)
    db.commit()
    for c in clients:
        db.refresh(c)

    deadlines = [
        # overdue
        TaxDeadline(
            client_id=clients[0].id,
            deadline_type=DeadlineType.VAT,
            due_date=today - timedelta(days=1),
            payment_amount=Decimal("100.00"),
        ),
        # red (<=2 days)
        TaxDeadline(
            client_id=clients[1].id,
            deadline_type=DeadlineType.ANNUAL_REPORT,
            due_date=today + timedelta(days=1),
            payment_amount=Decimal("200.00"),
        ),
        # yellow (<=7 days)
        TaxDeadline(
            client_id=clients[2].id,
            deadline_type=DeadlineType.ADVANCE_PAYMENT,
            due_date=today + timedelta(days=5),
            payment_amount=Decimal("300.00"),
        ),
        # green (not urgent, but upcoming should include if within 7? no, >7 so excluded)
        TaxDeadline(
            client_id=clients[2].id,
            deadline_type=DeadlineType.OTHER,
            due_date=today + timedelta(days=10),
            payment_amount=Decimal("400.00"),
        ),
    ]
    db.add_all(deadlines)
    db.commit()
    for d in deadlines:
        db.refresh(d)
    return deadlines


def test_dashboard_urgent_deadlines(client, test_db, advisor_headers):
    _seed_deadlines(test_db)

    resp = client.get("/api/v1/tax-deadlines/dashboard/urgent", headers=advisor_headers)
    assert resp.status_code == 200
    data = resp.json()

    urgent = data["urgent"]
    urgencies = {item["urgency"] for item in urgent}
    assert {"overdue", "red", "yellow"} == urgencies

    # payment amounts are serialized as floats
    amount_map = {item["urgency"]: item["payment_amount"] for item in urgent}
    assert amount_map["overdue"] == 100.0
    assert amount_map["red"] == 200.0
    assert amount_map["yellow"] == 300.0

    upcoming = data["upcoming"]
    # upcoming should include red/yellow (due within 7 days) but not overdue or >7 days
    assert len(upcoming) == 2
    due_dates = {item["due_date"] for item in upcoming}
    today = date.today()
    assert due_dates == { (today + timedelta(days=1)).isoformat(), (today + timedelta(days=5)).isoformat() }
