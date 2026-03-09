from datetime import date
from decimal import Decimal

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.advance_payment_service import AdvancePaymentService
from app.clients.models import Client, ClientType


def _client(db, idx: int) -> Client:
    client = Client(
        full_name=f"AP Overview Client {idx}",
        id_number=f"APOV-{idx}",
        client_type=ClientType.COMPANY,
        opened_at=date.today(),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def test_list_overview_returns_rows_sorted_and_total(test_db):
    c1 = _client(test_db, 1)
    c2 = _client(test_db, 2)
    repo = AdvancePaymentRepository(test_db)
    repo.create(client_id=c2.id, year=2026, month=1, due_date=date(2026, 2, 15), expected_amount=Decimal("100"))
    paid = repo.create(
        client_id=c1.id,
        year=2026,
        month=2,
        due_date=date(2026, 3, 15),
        expected_amount=Decimal("200"),
    )
    repo.update(paid, status=AdvancePaymentStatus.PAID, paid_amount=Decimal("200"))

    service = AdvancePaymentService(test_db)
    rows, total = service.list_overview(
        year=2026,
        month=None,
        statuses=[AdvancePaymentStatus.PENDING, AdvancePaymentStatus.PAID],
        page=1,
        page_size=10,
    )

    assert total == 2
    # Sorted by client name asc (C1 before C2)
    assert rows[0][1] == c1.full_name
    assert rows[1][1] == c2.full_name


def test_get_overview_kpis_collection_rate_rounds(test_db):
    client = _client(test_db, 3)
    repo = AdvancePaymentRepository(test_db)
    partial = repo.create(
        client_id=client.id,
        year=2026,
        month=1,
        due_date=date(2026, 2, 15),
        expected_amount=Decimal("100"),
    )
    repo.update(partial, paid_amount=Decimal("50"), status=AdvancePaymentStatus.PARTIAL)

    paid = repo.create(
        client_id=client.id,
        year=2026,
        month=2,
        due_date=date(2026, 3, 15),
        expected_amount=Decimal("200"),
    )
    repo.update(paid, paid_amount=Decimal("200"), status=AdvancePaymentStatus.PAID)

    service = AdvancePaymentService(test_db)
    kpis = service.get_overview_kpis(
        year=2026, statuses=[AdvancePaymentStatus.PARTIAL, AdvancePaymentStatus.PAID]
    )

    assert kpis["total_expected"] == 300.0
    assert kpis["total_paid"] == 250.0
    assert kpis["collection_rate"] == round(250.0 / 300.0 * 100, 2)
