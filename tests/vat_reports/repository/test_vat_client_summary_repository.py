from datetime import date

from app.businesses.models.business import Business
from app.common.enums import VatType
from app.clients.models.client import Client
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.repositories.vat_client_summary_repository import VatClientSummaryRepository
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository


def _user(test_db) -> User:
    user = User(
        full_name="VAT Summary Repo User",
        email="vat.summary.repo@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _business(test_db) -> Business:
    client = Client(full_name="VAT Summary Client", id_number="VAT-SUM-1")
    test_db.add(client)
    test_db.flush()
    business = Business(
        client_id=client.id,
        business_name=client.full_name,
        opened_at=date(2026, 1, 1),
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(client)
    test_db.refresh(business)
    return business


def test_vat_client_summary_repository_periods_and_annual_aggregates(test_db):
    user = _user(test_db)
    business = _business(test_db)
    work_repo = VatWorkItemRepository(test_db)
    summary_repo = VatClientSummaryRepository(test_db)

    i1 = work_repo.create(
        business.id,
        "2026-02",
        VatType.MONTHLY,
        user.id,
        status=VatWorkItemStatus.MATERIAL_RECEIVED,
    )
    i2 = work_repo.create(
        business.id,
        "2026-01",
        VatType.MONTHLY,
        user.id,
        status=VatWorkItemStatus.FILED,
    )

    work_repo.update_vat_totals(i1.id, total_output_vat=170.0, total_input_vat=20.0, total_output_net=1000.0, total_input_net=200.0)
    work_repo.update_vat_totals(i2.id, total_output_vat=85.0, total_input_vat=10.0, total_output_net=500.0, total_input_net=100.0)

    periods = summary_repo.get_periods_for_business(business.id)
    assert [work_item.period for work_item, _output_net, _input_net in periods] == ["2026-02", "2026-01"]

    annual = summary_repo.get_annual_aggregates(business.id)
    assert len(annual) == 1
    assert annual[0]["year"] == 2026
    assert float(annual[0]["total_output_vat"]) == 255.0
    assert float(annual[0]["total_input_vat"]) == 30.0
    assert float(annual[0]["net_vat"]) == 225.0
    assert annual[0]["periods_count"] == 2
    assert annual[0]["filed_count"] == 1


def test_vat_work_item_repository_list_by_business(test_db):
    user = _user(test_db)
    b1 = _business(test_db)

    client2 = Client(full_name="VAT Summary Client 2", id_number="VAT-SUM-2")
    test_db.add(client2)
    test_db.flush()
    b2 = Business(
        client_id=client2.id,
        business_name=client2.full_name,
        opened_at=date(2026, 1, 1),
    )
    test_db.add(b2)
    test_db.commit()
    test_db.refresh(client2)
    test_db.refresh(b2)

    repo = VatWorkItemRepository(test_db)
    a = repo.create(b1.id, "2026-03", VatType.MONTHLY, user.id)
    b = repo.create(b1.id, "2026-01", VatType.MONTHLY, user.id)
    repo.create(b2.id, "2026-02", VatType.MONTHLY, user.id)

    rows = repo.list_by_business(b1.id)
    assert [r.id for r in rows] == [a.id, b.id]


def test_vat_work_item_repository_list_by_business_applies_limit(test_db):
    user = _user(test_db)
    business = _business(test_db)
    repo = VatWorkItemRepository(test_db)

    for month in range(1, 301):
        year = 2026 + (month - 1) // 12
        month_in_year = ((month - 1) % 12) + 1
        repo.create(business.id, f"{year:04d}-{month_in_year:02d}", VatType.MONTHLY, user.id)

    rows = repo.list_by_business(business.id)

    assert len(rows) == 200
    assert rows[0].period == "2050-12"
    assert rows[-1].period == "2034-05"
