"""Integration tests for vat_work_item_grouped_repository."""

from datetime import timedelta

from app.users.models.user import User, UserRole
from app.users.services.auth_service import AuthService
from app.vat_reports.repositories.vat_work_item_grouped_repository import list_due_date_groups
from tests.helpers.identity import seed_client_identity
from tests.helpers.tax_calendar_links import create_linked_vat_work_item


def _user(db):
    user = User(
        full_name="Grouped Repo Test User",
        email="grouped.repo.test@example.com",
        password_hash=AuthService.hash_password("pass"),
        role=UserRole.ADVISOR,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def test_grouped_due_date_uses_due_date_effective_not_online_extension(test_db):
    """Group key must equal due_date_effective (statutory), not due_date_effective + 4 days."""
    user = _user(test_db)
    client = seed_client_identity(test_db, full_name="Grouped Client", id_number="GC001")

    item = create_linked_vat_work_item(
        test_db,
        client_record_id=client.id,
        period="2026-08",
        created_by=user.id,
    )
    test_db.commit()

    groups = list_due_date_groups(test_db)

    assert len(groups) == 1
    group = groups[0]
    assert group["due_date"] == item.due_date_effective
    assert group["due_date"] != item.due_date_effective + timedelta(days=4)
