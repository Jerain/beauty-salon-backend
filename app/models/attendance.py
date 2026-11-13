"""Attendance models."""
import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Boolean, ForeignKey, Integer, Numeric, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class AttendanceApprove(Base):
    __tablename__ = "attendance_approves"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("attendance_records.id"), nullable=False)
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    adjust_type: Mapped[str] = mapped_column(String(20), nullable=False)  # late/early_leave/absent
    adjust_remark: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/approved/rejected
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    record: Mapped["AttendanceRecord"] = relationship(foreign_keys=[record_id])
    staff: Mapped["Staff"] = relationship(foreign_keys=[staff_id])


class AttendanceRule(Base):
    __tablename__ = "attendance_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    work_start_time: Mapped[str] = mapped_column(String(10), default="09:00")
    work_end_time: Mapped[str] = mapped_column(String(10), default="18:00")
    late_threshold: Mapped[int] = mapped_column(Integer, default=10)  # minutes
    early_leave_threshold: Mapped[int] = mapped_column(Integer, default=10)
    geofence_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    geofence_latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    geofence_longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    geofence_radius: Mapped[int | None] = mapped_column(Integer)  # meters
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    clock_in_time: Mapped[datetime | None] = mapped_column(DateTime)
    clock_out_time: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="normal")  # normal/late/early_leave/absent
    clock_in_location: Mapped[str | None] = mapped_column(String(100))
    clock_out_location: Mapped[str | None] = mapped_column(String(100))
    remark: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    staff: Mapped["Staff"] = relationship()
