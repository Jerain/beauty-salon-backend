"""SkinTestResult model with pgvector support."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class SkinTestResult(Base):
    __tablename__ = "skin_tests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(100))
    test_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Scores
    overall_score: Mapped[int | None] = mapped_column(Integer)
    skin_type: Mapped[str | None] = mapped_column(String(30))  # dry/oily/combination/sensitive/etc.

    # 8 dimensions
    pore_score: Mapped[int | None] = mapped_column(Integer)
    pore_count: Mapped[int | None] = mapped_column(Integer)
    pore_diameter: Mapped[float | None] = mapped_column(Numeric(6, 2))

    acne_score: Mapped[int | None] = mapped_column(Integer)
    acne_count: Mapped[int | None] = mapped_column(Integer)

    spot_score: Mapped[int | None] = mapped_column(Integer)
    spot_area: Mapped[float | None] = mapped_column(Numeric(6, 2))

    wrinkle_score: Mapped[int | None] = mapped_column(Integer)
    wrinkle_count: Mapped[int | None] = mapped_column(Integer)

    skin_color_score: Mapped[int | None] = mapped_column(Integer)
    skin_brightness: Mapped[int | None] = mapped_column(Integer)

    moisture_score: Mapped[int | None] = mapped_column(Integer)
    moisture_index: Mapped[int | None] = mapped_column(Integer)

    sensitive_score: Mapped[int | None] = mapped_column(Integer)
    sensitive_level: Mapped[str | None] = mapped_column(String(20))  # mild/moderate/severe

    blackhead_score: Mapped[int | None] = mapped_column(Integer)
    blackhead_count: Mapped[int | None] = mapped_column(Integer)

    # Images
    front_image: Mapped[str | None] = mapped_column(String(500))
    left_image: Mapped[str | None] = mapped_column(String(500))
    right_image: Mapped[str | None] = mapped_column(String(500))

    remark: Mapped[str | None] = mapped_column(Text)
    report_url: Mapped[str | None] = mapped_column(String(500))
    operator_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship()
