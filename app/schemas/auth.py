from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: int
    full_name: str
    role: UserRole

    model_config = {"from_attributes": True}
