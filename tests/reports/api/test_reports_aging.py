from datetime import date, timedelta
from decimal import Decimal
from itertools import count

from app.charge.models.charge import Charge, ChargeStatus, ChargeType
from app.clients.models import Client, ClientType


_client_seq = count(1)


def _client(db) -> Client:
    client = Client(
        full_name=f"Aging Client {next(_client_seq)}",
        id_number=f"11111111{next(_client_seq)}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def _charge(db, client_id: int, amount: Decimal, issued_days_ago: int):
    issued_at = date.today() - timedelta(days=issued_days_ago)
    charge = Charge(
        client_id=client_id,
        amount=amount,
        currency="ILS",
        charge_type=ChargeType.ONE_TIME,
        status=ChargeStatus.ISSUED,
        issued_at=issued_at,
        created_at=issued_at,
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


def test_aging_report_buckets_and_sorting(client, test_db, advisor_headers):
    client_a = _client(test_db)
    client_b = _client(test_db)

    # Client A: mix across buckets
    _charge(test_db, client_a.id, Decimal("100"), issued_days_ago=10)   # current
    _charge(test_db, client_a.id, Decimal("200"), issued_days_ago=45)   # 30
    _charge(test_db, client_a.id, Decimal("300"), issued_days_ago=75)   # 60
    _charge(test_db, client_a.id, Decimal("400"), issued_days_ago=120)  # 90+

    # Client B: single 90+ should sort below A because total is smaller
    _charge(test_db, client_b.id, Decimal("150"), issued_days_ago=200)

    resp = client.get("/api/v1/reports/aging", headers=advisor_headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_outstanding"] == 1_150.0
    assert body["summary"]["total_current"] == 100.0
    assert body["summary"]["total_30_days"] == 200.0
    assert body["summary"]["total_60_days"] == 300.0
    assert body["summary"]["total_90_plus"] == 550.0

    items = body["items"]
    assert len(items) == 2
    # Sorted by total outstanding desc
    assert items[0]["client_id"] == client_a.id
    assert items[0]["current"] == 100.0
    assert items[0]["days_30"] == 200.0
    assert items[0]["days_60"] == 300.0
    assert items[0]["days_90_plus"] == 400.0
    assert items[0]["total_outstanding"] == 1_000.0
    assert items[0]["oldest_invoice_days"] >= 120


def test_aging_report_respects_cap_flag(client, test_db, advisor_headers):
    # Create more than limit to trigger capped True
    for _ in range(2001):
        c = _client(test_db)
        _charge(test_db, c.id, Decimal("1"), issued_days_ago=5)

    resp = client.get("/api/v1/reports/aging", headers=advisor_headers)
    assert resp.status_code == 200
    assert resp.json()["capped"] is True
    assert resp.json()["cap_limit"] == 2000
