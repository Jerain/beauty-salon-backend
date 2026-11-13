"""CardType, MemberCard, CardTransaction models - Core module."""
import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, DateTime, Date, Boolean, ForeignKey, Integer, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class CardType(Base):
    __tablename__ = "card_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    card_category: Mapped[str] = mapped_column(String(20), nullable=False)  # stored_value/times/period/discount/point/package
    sell_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    face_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    present_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    present_items: Mapped[dict | None] = mapped_column(JSON)
    validity_type: Mapped[str] = mapped_column(String(20), default="permanent")  # permanent/fixed/days
    validity_days: Mapped[int | None] = mapped_column(Integer)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    consume_rule: Mapped[dict | None] = mapped_column(JSON)
    applicable_shops: Mapped[list | None] = mapped_column(JSON)  # 适用门店ID列表
    description: Mapped[str | None] = mapped_column(Text)
    shop_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MemberCard(Base):
    __tablename__ = "member_cards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    card_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("card_types.id"), nullable=False)
    card_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    principal_balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    present_balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    total_times: Mapped[int | None] = mapped_column(Integer)
    remaining_times: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/frozen/expired/refunded/used_up
    activate_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expire_date: Mapped[datetime | None] = mapped_column(DateTime)
    remark: Mapped[str | None] = mapped_column(Text)
    shop_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="member_cards")
    card_type: Mapped["CardType"] = relationship()
    transactions: Mapped[list["CardTransaction"]] = relationship(back_populates="member_card", cascade="all, delete-orphan")


class CardTransaction(Base):
    __tablename__ = "card_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_card_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("member_cards.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"))
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # consume/recharge/adjust/refund/gift
    principal_change: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    present_change: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    times_change: Mapped[int | None] = mapped_column(Integer)
    before_principal: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    after_principal: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    before_present: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    after_present: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    before_times: Mapped[int | None] = mapped_column(Integer)
    after_times: Mapped[int | None] = mapped_column(Integer)
    operator_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    member_card: Mapped["MemberCard"] = relationship(back_populates="transactions")
