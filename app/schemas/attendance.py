"""Attendance schemas."""
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel


class AttendanceRuleResponse(BaseModel):
    id: UUID
    shop_id: UUID
    work_start_time: str
    work_end_time: str
    late_threshold: int
    early_leave_threshold: int
    geofence_enabled: bool
    geofence_latitude: float | None = None
    geofence_longitude: float | None = None
    geofence_radius: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendanceRuleCreate(BaseModel):
    work_start_time: str = "09:00"
    work_end_time: str = "18:00"
    late_threshold: int = 10
    early_leave_threshold: int = 10
    geofence_enabled: bool = False
    geofence_latitude: float | None = None
    geofence_longitude: float | None = None
    geofence_radius: int | None = None


class AttendanceRuleUpdate(BaseModel):
    work_start_time: str | None = None
    work_end_time: str | None = None
    late_threshold: int | None = None
    early_leave_threshold: int | None = None
    geofence_enabled: bool | None = None
    geofence_latitude: float | None = None
    geofence_longitude: float | None = None
    geofence_radius: int | None = None


class AttendanceRecordResponse(BaseModel):
    id: UUID
    staff_id: UUID
    staff_name: str | None = None
    shop_id: UUID
    record_date: date
    clock_in_time: datetime | None = None
    clock_out_time: datetime | None = None
    status: str
    clock_in_location: str | None = None
    clock_out_location: str | None = None
    remark: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ClockInRequest(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    location: str | None = None


class ClockOutRequest(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    location: str | None = None


class AttendanceApproveRequest(BaseModel):
    record_id: UUID
    reason: str
    adjust_type: str = "late"  # late/early_leave/absent
    adjust_remark: str | None = None


class AttendanceApproveResponse(BaseModel):
    id: UUID
    record_id: UUID
    staff_id: UUID | None = None
    reason: str
    adjust_type: str
    status: str  # pending/approved/rejected
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendanceStatisticResponse(BaseModel):
    staff_id: UUID
    staff_name: str | None = None
    month: str
    work_days: int = 0
    actual_days: int = 0
    late_count: int = 0
    early_leave_count: int = 0
    absent_count: int = 0
