from datetime import date, timedelta
from itertools import count

from app.annual_reports.models.annual_report_enums import SubmissionMethod
from app.businesses.models.business import Business, EntityType
from app.businesses.models.business_tax_profile import VatType
from app.clients.models.client import Client
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


def _business(db) -> Business:
    idx = next(_client_seq)
    client = Client(full_name=f"VAT Work Repo Client {idx}", id_number=f"VWR{idx:03d}")
    db.add(client)
    db.commit()
    db.refresh(client)
    return db.get(Business, client.id)


def test_status_listing_totals_and_audit_trail(test_db):
    repo = VatWorkItemRepository(test_db)
    user = _user(test_db)
    business = _business(test_db)
    now = utcnow()

    oldest = repo.create(
        business_id=business.id,
        period="2026-01",
        period_type=VatType.MONTHLY,
        created_by=user.id,
        status=VatWorkItemStatus.MATERIAL_RECEIVED,
    )
    newest = repo.create(
        business_id=business.id,
        period="2026-03",
        period_type=VatType.MONTHLY,
        created_by=user.id,
        status=VatWorkItemStatus.PENDING_MATERIALS,
    )
    middle = repo.create(
        business_id=business.id,
        period="2026-02",
        period_type=VatType.MONTHLY,
        created_by=user.id,
        status=VatWorkItemStatus.PENDING_MATERIALS,
    )

    by_status = repo.list_by_status(VatWorkItemStatus.PENDING_MATERIALS, page=1, page_size=10)
    assert [item.id for item in by_status] == [newest.id, middle.id]
    assert repo.count_by_status(VatWorkItemStatus.PENDING_MATERIALS) == 2

    all_items = repo.list_all(page=1, page_size=10)
    assert [item.period for item in all_items] == ["2026-03", "2026-02", "2026-01"]
    assert repo.count_all() == 3

    updated = repo.update_vat_totals(
        oldest.id,
        total_output_vat=170.0,
        total_input_vat=20.0,
        total_output_net=1000.0,
        total_input_net=200.0,
    )
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


def test_mark_filed_persists_amendment_and_reference_fields(test_db):
    repo = VatWorkItemRepository(test_db)
    user = _user(test_db)
    business = _business(test_db)
    item = repo.create(
        business_id=business.id,
        period="2026-11",
        period_type=VatType.MONTHLY,
        created_by=user.id,
    )

    filed = repo.mark_filed(
        item_id=item.id,
        final_vat_amount=321.5,
        submission_method=SubmissionMethod.ONLINE,
        filed_by=user.id,
        is_overridden=True,
        override_justification="manual override",
        submission_reference="REF-321",
        is_amendment=True,
        amends_item_id=999,
    )

    assert filed is not None
    assert filed.status == VatWorkItemStatus.FILED
    assert float(filed.final_vat_amount) == 321.5
    assert filed.submission_reference == "REF-321"
    assert filed.is_amendment is True
    assert filed.amends_item_id == 999

    assert repo.mark_filed(
        item_id=999999,
        final_vat_amount=1.0,
        submission_method=SubmissionMethod.MANUAL,
        filed_by=user.id,
    ) is None
