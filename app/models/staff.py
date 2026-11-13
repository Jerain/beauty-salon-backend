"""Staff and Position models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    staff: Mapped[list["Staff"]] = relationship(back_populates="position")


class Staff(Base):
    __tablename__ = "staff"

    # Role constants
    ROLE_SUPER_ADMIN = "super_admin"
    ROLE_BRAND_MANAGER = "brand_manager"
    ROLE_SHOP_MANAGER = "shop_manager"
    ROLE_CASHIER = "cashier"
    ROLE_BEAUTICIAN = "beautician"
    ROLE_STAFF = "staff"

    # Roles that can access all shops under a brand
    BRAND_LEVEL_ROLES = (ROLE_SUPER_ADMIN, ROLE_BRAND_MANAGER)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"))
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    position_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("positions.id"))
    role: Mapped[str] = mapped_column(String(20), default="staff")  # super_admin/brand_manager/shop_manager/cashier/beautician/staff
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_on_duty: Mapped[bool] = mapped_column(Boolean, default=True)
    bio: Mapped[str | None] = mapped_column(Text)
    hire_date: Mapped[datetime | None] = mapped_column(DateTime)
    points: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shop: Mapped["Shop"] = relationship(back_populates="staff")
    brand: Mapped["Brand | None"] = relationship(back_populates="staff")  # noqa: F821
    position: Mapped["Position | None"] = relationship(back_populates="staff")

    @property
    def is_brand_level(self) -> bool:
        """Whether this staff can access all shops under the brand."""
        return self.role in self.BRAND_LEVEL_ROLES
