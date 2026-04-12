from datetime import UTC, datetime, timedelta

from app.businesses.models.business import Business
from app.common.enums import VatType
from app.clients.models.client import Client
from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.vat_reports.services.vat_report_service import VatReportService


def _user(test_db) -> User:
    user = User(
        full_name="VAT Query User",
        email="vat.query.user@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _business(test_db) -> Business:
    client = Client(full_name="VAT Query Client", id_number="VQS001")
    test_db.add(client)
    test_db.commit()
    test_db.refresh(client)
    return test_db.get(Business, client.id)


def test_list_all_work_items_and_get_audit_trail(test_db):
    user = _user(test_db)
    business = _business(test_db)
    service = VatReportService(test_db)
    now = datetime.now(UTC)

    older = service.work_item_repo.create(
        business_id=business.id,
        period="2026-01",
        period_type=VatType.MONTHLY,
        created_by=user.id,
    )
    newer = service.work_item_repo.create(
        business_id=business.id,
        period="2026-02",
        period_type=VatType.MONTHLY,
        created_by=user.id,
    )

    items, total = service.list_all_work_items(page=1, page_size=1)
    assert total == 2
    assert [item.id for item in items] == [newer.id]

    late = service.work_item_repo.append_audit(work_item_id=older.id, performed_by=user.id, action="late")
    early = service.work_item_repo.append_audit(work_item_id=older.id, performed_by=user.id, action="early")
    late.performed_at = now + timedelta(minutes=1)
    early.performed_at = now - timedelta(minutes=1)
    test_db.commit()

    trail = service.get_audit_trail(older.id)
    assert [entry.action for entry in trail] == ["early", "late"]
