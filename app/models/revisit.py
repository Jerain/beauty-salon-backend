"""Revisit, ServiceLog, RevisitScript, TargetPlan models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class RevisitTask(Base):
    __tablename__ = "revisit_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    revisit_type: Mapped[str] = mapped_column(String(20), nullable=False)  # birthday/post_service/lost/routine
    planned_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/completed/cancelled/expired
    priority: Mapped[str] = mapped_column(String(10), default="medium")  # high/medium/low
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship()
    staff: Mapped["Staff"] = relationship()


class RevisitRecord(Base):
    __tablename__ = "revisit_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("revisit_tasks.id"))
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False)
    revisit_method: Mapped[str] = mapped_column(String(20), nullable=False)  # phone/wechat/visit
    result: Mapped[str] = mapped_column(String(20), nullable=False)  # visited/booked/no_interest/lost
    content: Mapped[str | None] = mapped_column(Text)
    next_plan: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship()
    staff: Mapped["Staff"] = relationship()


class ServiceLog(Base):
    __tablename__ = "service_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("service_projects.id"))
    service_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration: Mapped[int | None] = mapped_column(Integer)  # minutes
    before_images: Mapped[str | None] = mapped_column(Text)  # JSON array of URLs
    after_images: Mapped[str | None] = mapped_column(Text)  # JSON array of URLs
    remark: Mapped[str | None] = mapped_column(Text)
    customer_feedback: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="completed")  # in_progress/completed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship()
    staff: Mapped["Staff"] = relationship()


class RevisitScript(Base):
    __tablename__ = "revisit_scripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # birthday/post_service/lost/routine
    content: Mapped[str] = mapped_column(Text, nullable=False)
    scenario: Mapped[str | None] = mapped_column(Text)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    shop_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TargetPlan(Base):
    __tablename__ = "target_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)  # revenue/new_cards/recharge/new_customers/revisit
    target_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    actual_value: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    staff: Mapped["Staff | None"] = relationship()
