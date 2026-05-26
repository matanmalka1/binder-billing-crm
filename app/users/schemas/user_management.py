from pydantic import BaseModel, EmailStr, Field, model_validator

from app.core.api_types import ApiDateTime, PaginatedResponse
from app.users.models.user import UserRole
from app.users.models.user_audit_log import AuditAction, AuditStatus
from app.users.services.user_management_policies import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
)


class UserCreateRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    role: UserRole
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    role: UserRole | None = None
    email: EmailStr | None = None

    @model_validator(mode="after")
    def require_at_least_one(self) -> "UserUpdateRequest":
        if not any([self.full_name, self.phone, self.role, self.email]):
            raise ValueError("יש לספק לפחות שדה אחד לעדכון")
        return self


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class UserManagementResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None = None
    role: UserRole
    is_active: bool
    created_at: ApiDateTime
    last_login_at: ApiDateTime | None = None

    model_config = {"from_attributes": True}


UserManagementListResponse = PaginatedResponse[UserManagementResponse]


class UserAuditLogResponse(BaseModel):
    id: int
    action: AuditAction
    actor_user_id: int | None = None
    target_user_id: int | None = None
    email: str | None = None
    status: AuditStatus
    reason: str | None = None
    metadata: dict | None = None
    created_at: ApiDateTime

    model_config = {"from_attributes": True}


UserAuditLogListResponse = PaginatedResponse[UserAuditLogResponse]
