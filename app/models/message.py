"""Message models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(30), nullable=False)  # card_expire/recharge/birthday/no_visit/appointment/system
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    related_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    related_type: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MessageSetting(Base):
    __tablename__ = "message_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    card_expire_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    card_expire_days: Mapped[int] = mapped_column(Integer, default=7)
    recharge_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    birthday_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    birthday_days: Mapped[int] = mapped_column(Integer, default=3)
    no_visit_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    no_visit_days: Mapped[int] = mapped_column(Integer, default=30)
    appointment_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    appointment_hours: Mapped[int] = mapped_column(Integer, default=2)
    wechat_notify_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    wechat_app_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
