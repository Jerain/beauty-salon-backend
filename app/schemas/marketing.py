"""Marketing schemas."""
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel


class CouponResponse(BaseModel):
    id: UUID
    name: str
    coupon_type: str
    discount_value: float
    min_amount: float
    applicable_type: str
    applicable_ids: str | None = None
    total_count: int
    used_count: int
    start_date: date
    end_date: date
    shop_id: UUID | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CouponCreate(BaseModel):
    name: str
    coupon_type: str  # full_reduction/discount/cash/experience
    discount_value: float
    min_amount: float = 0.0
    applicable_type: str = "all"
    applicable_ids: str | None = None
    total_count: int = 0
    start_date: date
    end_date: date


class CouponUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    total_count: int | None = None


class CouponUseRequest(BaseModel):
    coupon_id: UUID
    customer_id: UUID
    order_amount: float


class MarketingActivityResponse(BaseModel):
    id: UUID
    name: str
    activity_type: str
    description: str | None = None
    original_price: float | None = None
    activity_price: float | None = None
    group_size: int | None = None
    start_date: date
    end_date: date
    total_orders: int
    shop_id: UUID | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketingActivityCreate(BaseModel):
    name: str
    activity_type: str  # group_buy/flash_sale/promotion
    description: str | None = None
    original_price: float | None = None
    activity_price: float | None = None
    group_size: int | None = None
    start_date: date
    end_date: date


class MarketingActivityUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    description: str | None = None


class MarketingOverviewResponse(BaseModel):
    active_count: int = 0
    pending_verify: int = 0
    completed_count: int = 0
    total_orders: int = 0


class ThirdPartyVerifyRequest(BaseModel):
    code: str
    platform: str  # meituan/douyin/dianping
    customer_id: UUID | None = None


class ThirdPartyVerifyResponse(BaseModel):
    valid: bool
    platform: str
    code: str
    project_name: str | None = None
    original_price: float | None = None
    message: str = ""
