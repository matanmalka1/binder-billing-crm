from datetime import date, timedelta
from itertools import count

from app.clients.models import Client, ClientType
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.utils.time_utils import utcnow
from app.vat_reports.models.vat_enums import VatWorkItemStatus
from app.vat_reports.repositories.vat_work_item_repository import VatWorkItemRepository


_client_seq = count(1)


def _user(test_db) -> User:
    user = User(
        full_name="VAT Work Repo User",
        email="vat.work.repo@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _client(db) -> Client:
    idx = next(_client_seq)
    c = Client(
        full_name=f"VAT Work Repo Client {idx}",
        id_number=f"VWR{idx:03d}",
        client_type=ClientType.OSEK_MURSHE,
        opened_at=date.today(),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_status_listing_totals_and_audit_trail(test_db):
    repo = VatWorkItemRepository(test_db)
    user = _user(test_db)
    client = _client(test_db)
    now = utcnow()

    oldest = repo.create(
        client_id=client.id,
        period="2026-01",
        created_by=user.id,
        status=VatWorkItemStatus.MATERIAL_RECEIVED,
    )
    newest = repo.create(
        client_id=client.id,
        period="2026-03",
        created_by=user.id,
        status=VatWorkItemStatus.PENDING_MATERIALS,
    )
    middle = repo.create(
        client_id=client.id,
        period="2026-02",
        created_by=user.id,
        status=VatWorkItemStatus.PENDING_MATERIALS,
    )

    by_status = repo.list_by_status(VatWorkItemStatus.PENDING_MATERIALS, page=1, page_size=10)
    assert [item.id for item in by_status] == [newest.id, middle.id]
    assert repo.count_by_status(VatWorkItemStatus.PENDING_MATERIALS) == 2

    all_items = repo.list_all(page=1, page_size=10)
    assert [item.period for item in all_items] == ["2026-03", "2026-02", "2026-01"]
    assert repo.count_all() == 3

    updated = repo.update_vat_totals(oldest.id, total_output_vat=170.0, total_input_vat=20.0)
    assert float(updated.total_output_vat) == 170.0
    assert float(updated.total_input_vat) == 20.0
    assert float(updated.net_vat) == 150.0

    late = repo.append_audit(
        work_item_id=oldest.id,
        performed_by=user.id,
        action="late",
    )
    early = repo.append_audit(
        work_item_id=oldest.id,
        performed_by=user.id,
        action="early",
    )
    late.performed_at = now + timedelta(minutes=1)
    early.performed_at = now - timedelta(minutes=1)
    test_db.commit()

    trail = repo.get_audit_trail(oldest.id)
    assert [event.action for event in trail] == ["early", "late"]

