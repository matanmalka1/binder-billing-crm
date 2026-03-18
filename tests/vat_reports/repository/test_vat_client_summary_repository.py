from datetime import date
from decimal import Decimal

from app.clients.models import Client, ClientType
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


def _client(test_db) -> Client:
    c = Client(
        full_name="VAT Summary Client",
        id_number="VAT-SUM-1",
        client_type=ClientType.OSEK_MURSHE,
        opened_at=date.today(),
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


def test_vat_client_summary_repository_periods_and_annual_aggregates(test_db):
    user = _user(test_db)
    client = _client(test_db)
    work_repo = VatWorkItemRepository(test_db)
    summary_repo = VatClientSummaryRepository(test_db)

    i1 = work_repo.create(client.id, "2026-02", user.id, status=VatWorkItemStatus.MATERIAL_RECEIVED)
    i2 = work_repo.create(client.id, "2026-01", user.id, status=VatWorkItemStatus.FILED)

    work_repo.update_vat_totals(i1.id, total_output_vat=170.0, total_input_vat=20.0)
    work_repo.update_vat_totals(i2.id, total_output_vat=85.0, total_input_vat=10.0)

    periods = summary_repo.get_periods_for_client(client.id)
    assert [work_item.period for work_item, _output_net, _input_net in periods] == ["2026-02", "2026-01"]

    annual = summary_repo.get_annual_aggregates(client.id)
    assert len(annual) == 1
    assert annual[0]["year"] == 2026
    assert float(annual[0]["total_output_vat"]) == 255.0
    assert float(annual[0]["total_input_vat"]) == 30.0
    assert float(annual[0]["net_vat"]) == 225.0
    assert annual[0]["periods_count"] == 2
    assert annual[0]["filed_count"] == 1


def test_vat_work_item_repository_list_by_client(test_db):
    user = _user(test_db)
    c1 = _client(test_db)
    c2 = Client(
        full_name="VAT Summary Client 2",
        id_number="VAT-SUM-2",
        client_type=ClientType.OSEK_MURSHE,
        opened_at=date.today(),
    )
    test_db.add(c2)
    test_db.commit()
    test_db.refresh(c2)

    repo = VatWorkItemRepository(test_db)
    a = repo.create(c1.id, "2026-03", user.id)
    b = repo.create(c1.id, "2026-01", user.id)
    repo.create(c2.id, "2026-02", user.id)

    rows = repo.list_by_client(c1.id)
    assert [r.id for r in rows] == [a.id, b.id]
