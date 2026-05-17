from pydantic import BaseModel, EmailStr

from app.users.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    rememberMe: bool = False


class LoginResponse(BaseModel):
    token: str
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    full_name: str
    role: UserRole
    email: EmailStr
    model_config = {"from_attributes": True}


LoginResponse.model_rebuild()
