import pytest

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.users.models.user import UserRole
from app.users.services.user_management_service import UserManagementService


def test_user_management_create_and_update_validation(test_db, test_user):
    service = UserManagementService(test_db)

    created = service.create_user(
        actor_user_id=test_user.id,
        actor_role=UserRole.ADVISOR,
        full_name="New User",
        email="new.user@example.com",
        role=UserRole.SECRETARY,
        password="password123",
    )
    assert created.email == "new.user@example.com"

    with pytest.raises(ConflictError):
        service.create_user(
            actor_user_id=test_user.id,
            actor_role=UserRole.ADVISOR,
            full_name="Dup User",
            email="new.user@example.com",
            role=UserRole.SECRETARY,
            password="password123",
        )

    with pytest.raises(AppError):
        service.update_user(
            actor_user_id=test_user.id,
            actor_role=UserRole.ADVISOR,
            user_id=created.id,
        )

    with pytest.raises(AppError):
        service.update_user(
            actor_user_id=test_user.id,
            actor_role=UserRole.ADVISOR,
            user_id=created.id,
            token_version=2,
        )

    another = service.create_user(
        actor_user_id=test_user.id,
        actor_role=UserRole.ADVISOR,
        full_name="Another User",
        email="another.user@example.com",
        role=UserRole.SECRETARY,
        password="password123",
    )
    with pytest.raises(ConflictError):
        service.update_user(
            actor_user_id=test_user.id,
            actor_role=UserRole.ADVISOR,
            user_id=another.id,
            email=created.email,
        )


def test_user_management_activate_deactivate_not_found_and_self_guard(test_db, test_user):
    service = UserManagementService(test_db)
    with pytest.raises(NotFoundError):
        service.activate_user(test_user.id, UserRole.ADVISOR, 999999)
    with pytest.raises(NotFoundError):
        service.deactivate_user(test_user.id, UserRole.ADVISOR, 999999)

    with pytest.raises(ForbiddenError):
        service.deactivate_user(test_user.id, UserRole.ADVISOR, test_user.id)
