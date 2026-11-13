"""Auth schemas."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class LoginRequest(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    staff_id: UUID
    staff_name: str
    role: str
    shop_id: UUID
    shop_name: str
    brand_id: UUID | None = None
    brand_name: str = ""
    is_brand_level: bool = False


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserResponse(BaseModel):
    id: UUID
    name: str
    phone: str
    role: str
    avatar_url: str | None = None
    shop_id: UUID
    shop_name: str
    brand_id: UUID | None = None
    brand_name: str = ""
    is_brand_level: bool = False
    position_name: str | None = None

    model_config = {"from_attributes": True}
