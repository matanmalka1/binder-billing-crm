from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = Field(False, alias="rememberMe")

    model_config = {"populate_by_name": True}


class LoginResponse(BaseModel):
    token: str
    user: dict

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: int
    full_name: str
    role: UserRole

    model_config = {"from_attributes": True}
