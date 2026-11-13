"""Skin test schemas."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class SkinTestResultResponse(BaseModel):
    id: UUID
    customer_id: UUID
    shop_id: UUID
    device_id: str | None = None
    test_time: datetime

    overall_score: int | None = None
    skin_type: str | None = None

    pore_score: int | None = None
    pore_count: int | None = None
    pore_diameter: float | None = None

    acne_score: int | None = None
    acne_count: int | None = None

    spot_score: int | None = None
    spot_area: float | None = None

    wrinkle_score: int | None = None
    wrinkle_count: int | None = None

    skin_color_score: int | None = None
    skin_brightness: int | None = None

    moisture_score: int | None = None
    moisture_index: int | None = None

    sensitive_score: int | None = None
    sensitive_level: str | None = None

    blackhead_score: int | None = None
    blackhead_count: int | None = None

    front_image: str | None = None
    left_image: str | None = None
    right_image: str | None = None

    remark: str | None = None
    report_url: str | None = None
    operator_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SkinTestResultCreate(BaseModel):
    customer_id: UUID
    device_id: str | None = None

    overall_score: int | None = None
    skin_type: str | None = None

    pore_score: int | None = None
    pore_count: int | None = None
    pore_diameter: float | None = None

    acne_score: int | None = None
    acne_count: int | None = None

    spot_score: int | None = None
    spot_area: float | None = None

    wrinkle_score: int | None = None
    wrinkle_count: int | None = None

    skin_color_score: int | None = None
    skin_brightness: int | None = None

    moisture_score: int | None = None
    moisture_index: int | None = None

    sensitive_score: int | None = None
    sensitive_level: str | None = None

    blackhead_score: int | None = None
    blackhead_count: int | None = None

    front_image: str | None = None
    left_image: str | None = None
    right_image: str | None = None

    remark: str | None = None
    report_url: str | None = None


class SkinTestResultUpdate(BaseModel):
    remark: str | None = None
    report_url: str | None = None
    skin_type: str | None = None


class SkinTestCompareResponse(BaseModel):
    before: SkinTestResultResponse
    after: SkinTestResultResponse
    improvements: dict  # dimension -> delta
