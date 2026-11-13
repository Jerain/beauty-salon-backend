"""Revisit and ServiceLog schemas."""
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel

from app.schemas.types import BrowserDatetime


class RevisitTaskResponse(BaseModel):
    id: UUID
    customer_id: UUID
    customer_name: str | None = None
    staff_id: UUID
    staff_name: str | None = None
    shop_id: UUID
    revisit_type: str
    planned_date: datetime
    content: str | None = None
    status: str
    priority: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RevisitTaskCreate(BaseModel):
    customer_id: UUID
    staff_id: UUID
    revisit_type: str  # birthday/post_service/lost/routine
    planned_date: BrowserDatetime
    content: str | None = None
    priority: str = "medium"  # high/medium/low


class RevisitTaskUpdate(BaseModel):
    status: str | None = None
    content: str | None = None
    planned_date: BrowserDatetime | None = None
    priority: str | None = None


class RevisitRecordResponse(BaseModel):
    id: UUID
    task_id: UUID | None = None
    customer_id: UUID
    customer_name: str | None = None
    staff_id: UUID
    staff_name: str | None = None
    revisit_method: str  # phone/wechat/visit
    result: str  # visited/booked/no_interest/lost
    content: str | None = None
    next_plan: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RevisitRecordCreate(BaseModel):
    task_id: UUID | None = None
    customer_id: UUID
    revisit_method: str  # phone/wechat/visit
    result: str  # visited/booked/no_interest/lost
    content: str | None = None
    next_plan: str | None = None


class RevisitStatisticResponse(BaseModel):
    total_tasks: int = 0
    pending_count: int = 0
    completed_count: int = 0
    cancelled_count: int = 0
    expired_count: int = 0
    completion_rate: float = 0.0


# ============ Service Log ============

class ServiceLogResponse(BaseModel):
    id: UUID
    customer_id: UUID
    customer_name: str | None = None
    staff_id: UUID
    staff_name: str | None = None
    shop_id: UUID
    order_id: UUID | None = None
    project_id: UUID | None = None
    service_date: datetime
    duration: int | None = None
    before_images: list[str] | None = None
    after_images: list[str] | None = None
    remark: str | None = None
    customer_feedback: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceLogCreate(BaseModel):
    customer_id: UUID
    staff_id: UUID
    order_id: UUID | None = None
    project_id: UUID | None = None
    service_date: BrowserDatetime
    duration: int | None = None
    before_images: list[str] | None = None
    after_images: list[str] | None = None
    remark: str | None = None
    customer_feedback: str | None = None


# ============ Revisit Script Library ============

class RevisitScriptResponse(BaseModel):
    id: UUID
    title: str
    category: str
    content: str
    usage_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class RevisitScriptCreate(BaseModel):
    title: str
    category: str  # birthday/post_service/lost/routine
    content: str
    scenario: str | None = None


# ============ Target Plan ============

class TargetPlanResponse(BaseModel):
    id: UUID
    shop_id: UUID
    target_type: str  # revenue/new_cards/recharge/new_customers/revisit
    target_value: float
    actual_value: float = 0.0
    completion_rate: float = 0.0
    month: str
    staff_id: UUID | None = None
    staff_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TargetPlanCreate(BaseModel):
    target_type: str
    target_value: float
    month: str  # YYYY-MM
    staff_id: UUID | None = None
