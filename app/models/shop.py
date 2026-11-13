"""Shop and Room models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Shop(Base):
    __tablename__ = "shops"
    __table_args__ = (
        UniqueConstraint('brand_id', 'code', name='uq_brand_shop_code'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(20))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    brand: Mapped["Brand | None"] = relationship(back_populates="shops")  # noqa: F821
    rooms: Mapped[list["Room"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    staff: Mapped[list["Staff"]] = relationship(back_populates="shop")
    customers: Mapped[list["Customer"]] = relationship(back_populates="shop")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    beds: Mapped[int] = mapped_column(Integer, default=1)
    floor: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    shop: Mapped["Shop"] = relationship(back_populates="rooms")
