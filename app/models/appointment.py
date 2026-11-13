"""Appointment, Schedule, AppointmentSetting, TimeSlotOccupy models."""
import uuid
from datetime import datetime, date, time
from sqlalchemy import String, DateTime, Date, Time, Boolean, ForeignKey, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    schedule_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_type: Mapped[str] = mapped_column(String(20), nullable=False)  # morning/afternoon/evening/custom/rest
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    room_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("service_projects.id"))
    project_ids: Mapped[list | None] = mapped_column(JSON)  # 多项目预约
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, default=60)  # minutes
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/confirmed/arrived/completed/cancelled
    source: Mapped[str] = mapped_column(String(20), default="in-store")  # in-store/online/wechat
    remark: Mapped[str | None] = mapped_column(Text)
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer: Mapped["Customer"] = relationship()
    staff: Mapped["Staff"] = relationship(foreign_keys=[staff_id])
    room: Mapped["Room | None"] = relationship()
    project: Mapped["ServiceProject | None"] = relationship()


class AppointmentSetting(Base):
    """预约规则设置"""
    __tablename__ = "appointment_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    time_interval: Mapped[int] = mapped_column(Integer, default=30)  # 预约时间间隔(分钟)
    work_start_time: Mapped[str] = mapped_column(String(5), default="09:00")  # 每日开始时间
    work_end_time: Mapped[str] = mapped_column(String(5), default="21:00")  # 每日结束时间
    max_appointments_per_staff: Mapped[int] = mapped_column(Integer, default=10)  # 每人每日上限
    advance_booking_days: Mapped[int] = mapped_column(Integer, default=1)  # 最少提前天数
    min_cancel_hours: Mapped[int] = mapped_column(Integer, default=2)  # 最晚取消时间(小时)
    schedule_constraint: Mapped[bool] = mapped_column(Boolean, default=False)  # 仅在排班时间可预约
    arrival_notify: Mapped[bool] = mapped_column(Boolean, default=True)  # 预约前通知员工
    public_booking: Mapped[bool] = mapped_column(Boolean, default=False)  # 开启公众号预约
    auto_confirm: Mapped[bool] = mapped_column(Boolean, default=False)  # 自动确认
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TimeSlotOccupy(Base):
    """时段占位（非预约但锁定时间段）"""
    __tablename__ = "time_slot_occupies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    occupy_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(200))
    color: Mapped[str | None] = mapped_column(String(20))  # 占位颜色标记
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
