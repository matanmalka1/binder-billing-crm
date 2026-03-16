from datetime import date, timedelta

from app.clients.models import Client, ClientType
from app.tax_deadline.models.tax_deadline import DeadlineType
from app.tax_deadline.repositories.tax_deadline_repository import TaxDeadlineRepository


def _client(db) -> Client:
    c = Client(
        full_name="Tax Timeline Client",
        id_number="TT-001",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_tax_deadline_timeline_returns_sorted_with_labels(client, test_db, advisor_headers):
    crm_client = _client(test_db)
    repo = TaxDeadlineRepository(test_db)

    later = repo.create(
        client_id=crm_client.id,
        deadline_type=DeadlineType.ANNUAL_REPORT,
        due_date=date.today() + timedelta(days=15),
    )
    sooner = repo.create(
        client_id=crm_client.id,
        deadline_type=DeadlineType.ADVANCE_PAYMENT,
        due_date=date.today() + timedelta(days=3),
    )

    resp = client.get(
        f"/api/v1/tax-deadlines/timeline?client_id={crm_client.id}",
        headers=advisor_headers,
    )

    assert resp.status_code == 200
    items = resp.json()
    assert [i["id"] for i in items] == [sooner.id, later.id]
    assert items[0]["milestone_label"] == "תשלום מקדמה"
    assert items[1]["milestone_label"] == "הגשת דוח שנתי"
    assert items[0]["days_remaining"] <= items[1]["days_remaining"]
