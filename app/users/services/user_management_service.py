from typing import Optional
from sqlalchemy.orm import Session
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.users.models.user_audit_log import AuditAction, AuditStatus
from app.users.models.user import User, UserRole
from app.users.repositories.user_repository import UserRepository
from app.users.services.audit_log_service import AuditLogService
from app.users.services.auth_service import AuthService
from app.users.services.user_management_policies import (
    IMMUTABLE_UPDATE_FIELDS,
    ensure_advisor,
    validate_password,
)
class UserManagementService:
    """User lifecycle management and authorization enforcement."""

    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        self.audit_log_service = AuditLogService(db)
    def create_user(
        self,
        actor_user_id: int,
        actor_role: UserRole,
        full_name: str,
        email: str,
        role: UserRole,
        password: str,
        phone: Optional[str] = None,
    ) -> User:
        ensure_advisor(actor_role)
        validate_password(password)

        if self.user_repo.get_by_email(email):
            raise ConflictError(f"כבר קיים משתמש עם המייל {email}", "USER.CONFLICT")

        user = self.user_repo.create(
            full_name=full_name,
            email=email,
            password_hash=AuthService.hash_password(password),
            role=role,
            phone=phone,
        )
        self.audit_log_service.log(
            action=AuditAction.USER_CREATED,
            status=AuditStatus.SUCCESS,
            actor_user_id=actor_user_id,
            target_user_id=user.id,
        )
        return user
    def list_users(self, actor_role: UserRole, page: int, page_size: int):
        ensure_advisor(actor_role)
        items = self.user_repo.list(page=page, page_size=page_size)
        total = self.user_repo.count()
        return items, total
    def get_user(self, actor_role: UserRole, user_id: int) -> Optional[User]:
        ensure_advisor(actor_role)
        return self.user_repo.get_by_id(user_id)
    def update_user(
        self,
        actor_user_id: int,
        actor_role: UserRole,
        user_id: int,
        **fields,
    ) -> Optional[User]:
        ensure_advisor(actor_role)
        if "email" in fields:
            existing = self.user_repo.get_by_email(fields["email"])
            if existing and existing.id != user_id:
                raise ConflictError(f"כבר קיים משתמש עם המייל  {fields['email']}", "USER.CONFLICT")

        immutable_attempt = IMMUTABLE_UPDATE_FIELDS.intersection(fields.keys())
        if immutable_attempt:
            disallowed = ", ".join(sorted(immutable_attempt))
            raise AppError(
                f"לא ניתן לעדכן שדות שאינם ניתנים לשינוי: {disallowed}",
                "USER.INVALID_UPDATE",
            )

        if not fields:
            raise AppError("חובה לספק לפחות שדה אחד הניתן לשינוי", "USER.NO_FIELDS_PROVIDED")

        user = self.user_repo.update(user_id, **fields)
        if not user:
            return None

        self.audit_log_service.log(
            action=AuditAction.USER_UPDATED,
            status=AuditStatus.SUCCESS,
            actor_user_id=actor_user_id,
            target_user_id=user.id,
            metadata={"updated_fields": sorted(fields.keys())},
        )
        return user
    def activate_user(
        self, actor_user_id: int, actor_role: UserRole, user_id: int
    ) -> Optional[User]:
        ensure_advisor(actor_role)
        user = self.user_repo.activate(user_id)
        if not user:
            return None
        self.audit_log_service.log(
            action=AuditAction.USER_ACTIVATED,
            status=AuditStatus.SUCCESS,
            actor_user_id=actor_user_id,
            target_user_id=user.id,
        )
        return user
    def deactivate_user(
        self,
        actor_user_id: int,
        actor_role: UserRole,
        target_user_id: int,
    ) -> Optional[User]:
        ensure_advisor(actor_role)
        if actor_user_id == target_user_id:
            raise ForbiddenError("אינך יכול להשבית את החשבון שלך", "USER.FORBIDDEN")

        user = self.user_repo.deactivate_and_bump_token(target_user_id)
        if not user:
            return None

        self.audit_log_service.log(
            action=AuditAction.USER_DEACTIVATED,
            status=AuditStatus.SUCCESS,
            actor_user_id=actor_user_id,
            target_user_id=user.id,
        )
        return user
    def reset_password(
        self,
        actor_user_id: int,
        actor_role: UserRole,
        target_user_id: int,
        new_password: str,
    ) -> Optional[User]:
        ensure_advisor(actor_role)
        validate_password(new_password)

        password_hash = AuthService.hash_password(new_password)
        user = self.user_repo.set_password_and_bump_token(target_user_id, password_hash)
        if not user:
            return None

        self.audit_log_service.log(
            action=AuditAction.PASSWORD_RESET,
            status=AuditStatus.SUCCESS,
            actor_user_id=actor_user_id,
            target_user_id=user.id,
        )
        return user
