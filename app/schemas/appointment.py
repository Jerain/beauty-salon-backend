"""Appointment schemas."""
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel


# ============ Appointment ============

class AppointmentResponse(BaseModel):
    id: UUID
    customer_id: UUID
    customer_name: str | None = None
    staff_id: UUID
    staff_name: str | None = None
    shop_id: UUID
    room_id: UUID | None = None
    room_name: str | None = None
    project_id: UUID | None = None
    project_name: str | None = None
    project_ids: list | None = None
    appointment_date: date
    start_time: str
    duration: int
    status: str
    source: str | None = None
    remark: str | None = None
    cancel_reason: str | None = None
    confirmed_at: datetime | None = None
    arrived_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AppointmentCreate(BaseModel):
    customer_id: UUID
    staff_id: UUID
    room_id: UUID | None = None
    project_id: UUID | None = None
    project_ids: list[str] | None = None
    appointment_date: date
    start_time: str
    duration: int = 60
    remark: str | None = None
    source: str = "in-store"


class AppointmentBatchCreate(BaseModel):
    appointments: list[AppointmentCreate]


class AppointmentUpdate(BaseModel):
    staff_id: UUID | None = None
    room_id: UUID | None = None
    project_id: UUID | None = None
    project_ids: list[str] | None = None
    appointment_date: date | None = None
    start_time: str | None = None
    duration: int | None = None
    remark: str | None = None


class AppointmentStatusUpdate(BaseModel):
    status: str  # confirmed/arrived/completed/cancelled
    cancel_reason: str | None = None


# ============ Time Conflict Check ============

class ConflictCheckRequest(BaseModel):
    staff_id: UUID
    appointment_date: date
    start_time: str
    duration: int = 60
    exclude_id: UUID | None = None  # 编辑时排除自身


class ConflictCheckResponse(BaseModel):
    available: bool
    conflicts: list[dict] = []
    suggestion: str | None = None


# ============ Day Count ============

class DayCountResponse(BaseModel):
    date: str
    count: int
    confirmed_count: int = 0
    pending_count: int = 0


# ============ TimeSlotOccupy ============

class TimeSlotOccupyResponse(BaseModel):
    id: UUID
    staff_id: UUID
    staff_name: str | None = None
    occupy_date: date
    start_time: str
    end_time: str
    reason: str | None = None
    color: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TimeSlotOccupyCreate(BaseModel):
    staff_id: UUID
    occupy_date: date
    start_time: str
    end_time: str
    reason: str | None = None
    color: str | None = None


class TimeSlotOccupyUpdate(BaseModel):
    start_time: str | None = None
    end_time: str | None = None
    reason: str | None = None
    color: str | None = None


# ============ AppointmentSetting ============

class AppointmentSettingResponse(BaseModel):
    id: UUID
    shop_id: UUID
    time_interval: int
    work_start_time: str
    work_end_time: str
    max_appointments_per_staff: int
    advance_booking_days: int
    min_cancel_hours: int
    schedule_constraint: bool
    arrival_notify: bool
    public_booking: bool
    auto_confirm: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AppointmentSettingUpdate(BaseModel):
    time_interval: int | None = None
    work_start_time: str | None = None
    work_end_time: str | None = None
    max_appointments_per_staff: int | None = None
    advance_booking_days: int | None = None
    min_cancel_hours: int | None = None
    schedule_constraint: bool | None = None
    arrival_notify: bool | None = None
    public_booking: bool | None = None
    auto_confirm: bool | None = None
