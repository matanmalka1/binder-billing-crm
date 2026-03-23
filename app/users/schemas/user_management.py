import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.core.api_types import ApiDateTime
from app.users.models.user import UserRole
from app.users.models.user_audit_log import AuditAction, AuditStatus
from app.users.services.user_management_policies import MIN_PASSWORD_LENGTH


class UserCreateRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    email: Optional[EmailStr] = None

    @model_validator(mode="after")
    def require_at_least_one(self) -> "UserUpdateRequest":
        if not any([self.full_name, self.phone, self.role, self.email]):
            raise ValueError("יש לספק לפחות שדה אחד לעדכון")
        return self


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class UserManagementResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: ApiDateTime
    last_login_at: Optional[ApiDateTime] = None

    model_config = {"from_attributes": True}


class UserManagementListResponse(BaseModel):
    items: list[UserManagementResponse]
    page: int
    page_size: int
    total: int


class UserAuditLogResponse(BaseModel):
    id: int
    action: AuditAction
    actor_user_id: Optional[int] = None
    target_user_id: Optional[int] = None
    email: Optional[str] = None
    status: AuditStatus
    reason: Optional[str] = None
    metadata: Optional[dict] = None    
    created_at: ApiDateTime

    model_config = {"from_attributes": True}


class UserAuditLogListResponse(BaseModel):
    items: list[UserAuditLogResponse]
    page: int
    page_size: int
    total: int
