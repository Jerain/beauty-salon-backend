"""Marketing models - Coupon and MarketingActivity."""
import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, DateTime, Date, Boolean, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    coupon_type: Mapped[str] = mapped_column(String(20), nullable=False)  # full_reduction/discount/cash/experience
    discount_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    min_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    applicable_type: Mapped[str] = mapped_column(String(20), default="all")  # all/project/product
    applicable_ids: Mapped[str | None] = mapped_column(Text)  # comma-separated IDs
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    shop_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketingActivity(Base):
    __tablename__ = "marketing_activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # group_buy/flash_sale/promotion
    description: Mapped[str | None] = mapped_column(Text)
    original_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    activity_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    group_size: Mapped[int | None] = mapped_column(Integer)  # for group buy
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    shop_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/ended/cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
