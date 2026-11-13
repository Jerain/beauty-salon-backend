"""Bookkeeping model for income/expense records."""
import uuid
from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class BookkeepingRecord(Base):
    __tablename__ = "bookkeeping_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id"), nullable=False)
    record_type: Mapped[str] = mapped_column(String(20), nullable=False)  # expense/income
    category: Mapped[str] = mapped_column(String(50), default="other")
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    payment_method: Mapped[str | None] = mapped_column(String(50))
    related_order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff.id"))
    record_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
