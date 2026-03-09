from app.users.models.user import User, UserRole
from app.users.models.user_audit_log import AuditAction, AuditStatus
from app.users.repositories.user_audit_log_repository import UserAuditLogRepository
from app.users.repositories.user_repository import UserRepository
from app.users.services.auth_service import AuthService
from app.users.services.user_management_service import UserManagementService


def _managed_user(test_db, *, email: str) -> User:
    user = User(
        full_name="Managed Account",
        email=email,
        password_hash=AuthService.hash_password("password123"),
        role=UserRole.SECRETARY,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def test_list_users_and_reset_password(test_db, test_user):
    service = UserManagementService(test_db)
    user_repo = UserRepository(test_db)
    target = _managed_user(test_db, email="reset.target@example.com")
    _managed_user(test_db, email="reset.other@example.com")

    items, total = service.list_users(actor_role=UserRole.ADVISOR, page=1, page_size=10)
    assert total >= 3
    assert target.id in {u.id for u in items}

    before_token_version = user_repo.get_by_id(target.id).token_version
    updated = service.reset_password(
        actor_user_id=test_user.id,
        actor_role=UserRole.ADVISOR,
        target_user_id=target.id,
        new_password="newpassword123",
    )
    assert updated.id == target.id
    assert updated.token_version == before_token_version + 1
    assert AuthService.verify_password("newpassword123", updated.password_hash) is True

    audit_repo = UserAuditLogRepository(test_db)
    password_reset_logs = audit_repo.list(
        page=1,
        page_size=10,
        action=AuditAction.PASSWORD_RESET,
        target_user_id=target.id,
    )
    assert len(password_reset_logs) == 1
    assert password_reset_logs[0].status == AuditStatus.SUCCESS

    assert (
        service.reset_password(
            actor_user_id=test_user.id,
            actor_role=UserRole.ADVISOR,
            target_user_id=999999,
            new_password="newpassword123",
        )
        is None
    )
