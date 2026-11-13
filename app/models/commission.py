"""Commission models."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class CommissionRule(Base):
    __tablename__ = "commission_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)  # service/sales/recharge/step
    commission_rate: Mapped[float | None] = mapped_column(Numeric(5, 2))  # percentage
    commission_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))  # fixed amount
    step_rules: Mapped[dict | None] = mapped_column(JSON)  # [{"min": 0, "max": 5000, "rate": 5}, ...]
    shop_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CommissionRecord(Base):
    __tablename__ = "commission_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"))
    commission_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("commission_rules.id"))
    commission_type: Mapped[str] = mapped_column(String(20), nullable=False)  # service/sales/recharge/step
    base_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    commission_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    staff: Mapped["Staff"] = relationship()
