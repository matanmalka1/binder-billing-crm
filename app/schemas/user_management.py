from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models import AuditAction, AuditStatus, UserRole


class UserCreateRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole
    password: str = Field(min_length=8)


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    email: Optional[str] = None
    id: Optional[int] = None
    token_version: Optional[int] = None
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=8)


class UserManagementResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: Optional[str]
    role: UserRole
    is_active: bool
    token_version: int
    created_at: datetime
    last_login_at: Optional[datetime]

    model_config = {"from_attributes": True}


class UserManagementListResponse(BaseModel):
    items: list[UserManagementResponse]
    page: int
    page_size: int
    total: int


class UserAuditLogResponse(BaseModel):
    id: int
    action: AuditAction
    actor_user_id: Optional[int]
    target_user_id: Optional[int]
    email: Optional[str]
    status: AuditStatus
    reason: Optional[str]
    metadata: Optional[dict]
    created_at: datetime


class UserAuditLogListResponse(BaseModel):
    items: list[UserAuditLogResponse]
    page: int
    page_size: int
    total: int

