"""Customer schemas."""
from datetime import datetime, date
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel


class TagResponse(BaseModel):
    id: UUID
    name: str
    color: str | None = None

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str
    color: str | None = None


class SourceResponse(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class SourceCreate(BaseModel):
    name: str


class CustomerCreate(BaseModel):
    name: str
    phone: str
    gender: str | None = None
    birthday: date | None = None
    source_id: UUID | None = None
    staff_id: UUID | None = None
    level: str = "normal"
    remark: str | None = None
    taboo: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    gender: str | None = None
    birthday: date | None = None
    source_id: UUID | None = None
    staff_id: UUID | None = None
    level: str | None = None
    remark: str | None = None
    taboo: str | None = None


class CustomerResponse(BaseModel):
    id: UUID
    name: str
    code: str
    phone: str
    gender: str | None = None
    birthday: date | None = None
    avatar_url: str | None = None
    level: str
    balance: float
    points: int
    total_consumption: float
    remark: str | None = None
    taboo: str | None = None
    last_visit_at: datetime | None = None
    is_blacklisted: bool
    source_name: str | None = None
    staff_name: str | None = None
    tags: List[TagResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    id: UUID
    name: str
    code: str
    phone: str
    level: str
    balance: float
    points: int
    last_visit_at: datetime | None = None
    tags: List[TagResponse] = []

    model_config = {"from_attributes": True}
