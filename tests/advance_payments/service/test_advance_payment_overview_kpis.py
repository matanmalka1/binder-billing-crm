from datetime import date
from decimal import Decimal
from itertools import count

from app.advance_payments.models.advance_payment import AdvancePaymentStatus
from app.advance_payments.repositories.advance_payment_repository import AdvancePaymentRepository
from app.advance_payments.services.advance_payment_analytics_service import AdvancePaymentAnalyticsService as AdvancePaymentService
from app.businesses.models.business import Business, BusinessType
from app.clients.models.client import Client


_seq = count(1)


def _business(db, idx: int) -> Business:
    uniq = next(_seq)
    client = Client(
        full_name=f"AP Overview Client {idx}",
        id_number=f"321654{uniq:03d}",
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    business = Business(
        client_id=client.id,
        business_name=f"AP Overview Biz {idx}",
        business_type=BusinessType.COMPANY,
        opened_at=date.today(),
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def test_list_overview_returns_rows_sorted_and_total(test_db):
    b1 = _business(test_db, 1)
    b2 = _business(test_db, 2)
    repo = AdvancePaymentRepository(test_db)
    repo.create(business_id=b2.id, period="2026-01", period_months_count=1, due_date=date(2026, 2, 15), expected_amount=Decimal("100"))
    paid = repo.create(
        business_id=b1.id,
        period="2026-02",
        period_months_count=1,
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
    assert rows[0][1] == b1.business_name
    assert rows[1][1] == b2.business_name


def test_get_overview_kpis_collection_rate_rounds(test_db):
    business = _business(test_db, 3)
    repo = AdvancePaymentRepository(test_db)
    partial = repo.create(
        business_id=business.id,
        period="2026-01",
        period_months_count=1,
        due_date=date(2026, 2, 15),
        expected_amount=Decimal("100"),
    )
    repo.update(partial, paid_amount=Decimal("50"), status=AdvancePaymentStatus.PARTIAL)

    paid = repo.create(
        business_id=business.id,
        period="2026-02",
        period_months_count=1,
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
