"""Staff schemas."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class PositionResponse(BaseModel):
    id: UUID
    name: str
    sort_order: int

    model_config = {"from_attributes": True}


class PositionCreate(BaseModel):
    name: str
    sort_order: int = 0


class PositionUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class StaffResponse(BaseModel):
    id: UUID
    name: str
    phone: str
    avatar_url: str | None = None
    shop_id: UUID
    position_id: UUID | None = None
    position_name: str | None = None
    role: str
    is_active: bool
    is_on_duty: bool = True
    bio: str | None = None
    hire_date: datetime | None = None
    points: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StaffCreate(BaseModel):
    name: str
    phone: str
    password: str = "123456"
    position_id: UUID | None = None
    role: str = "staff"
    hire_date: datetime | None = None


class StaffUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    position_id: UUID | None = None
    role: str | None = None
    is_active: bool | None = None
    is_on_duty: bool | None = None
    bio: str | None = None
    hire_date: datetime | None = None
    avatar_url: str | None = None
