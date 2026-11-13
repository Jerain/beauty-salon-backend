"""Order schemas."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from typing import List


class OrderItemCreate(BaseModel):
    item_type: str
    item_id: UUID | None = None
    item_name: str
    quantity: int = 1
    unit_price: float
    discount: float = 100.0
    amount: float
    staff_id: UUID | None = None


class OrderItemResponse(BaseModel):
    id: UUID
    item_type: str
    item_name: str
    quantity: int
    unit_price: float
    discount: float
    amount: float
    staff_id: UUID | None = None

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    payment_method_id: UUID | None = None
    payment_method_name: str
    amount: float
    card_id: UUID | None = None
    is_arrears: bool = False  # 是否为补款


class PaymentResponse(BaseModel):
    id: UUID
    payment_method_name: str
    amount: float
    is_refund: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderRecordResponse(BaseModel):
    id: UUID
    action: str
    old_status: str | None = None
    new_status: str | None = None
    remark: str | None = None
    created_by: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: UUID
    order_no: str
    customer_id: UUID | None = None
    customer_name: str | None = None
    shop_id: UUID
    total_amount: float
    discount_amount: float
    paid_amount: float
    status: str
    hold_status: str | None = None
    order_type: str
    consume_type: str | None = None
    refund_reason: str | None = None
    refund_type: str | None = None
    refund_amount: float = 0.0
    refund_method: str | None = None
    verify_status: str = "unverified"
    verify_at: datetime | None = None
    remark: str | None = None
    items: List[OrderItemResponse] = []
    payments: List[PaymentResponse] = []
    records: List[OrderRecordResponse] = []
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    customer_id: UUID | None = None
    order_type: str = "service"
    consume_type: str | None = None
    remark: str | None = None
    items: List[OrderItemCreate]
    payments: List[PaymentCreate]


class OrderModifyRequest(BaseModel):
    """改单请求"""
    items: List[OrderItemCreate]
    payments: List[PaymentCreate]
    remark: str | None = None


class OrderCancelRequest(BaseModel):
    """撤销订单请求"""
    reason: str | None = None


class OrderRefundRequest(BaseModel):
    """退单请求"""
    refund_type: str  # full/part
    refund_amount: float
    refund_method: str  # 原路退回/退现金/退卡
    reason: str | None = None
    item_ids: List[UUID] | None = None  # 部分退单时的品项ID


class OrderHoldRequest(BaseModel):
    """挂单/取回挂单请求"""
    action: str  # hold挂单, restore取回
    remark: str | None = None


class OrderArrearsRequest(BaseModel):
    """补款请求"""
    payment: PaymentCreate
    remark: str | None = None


class OrderSignatureRequest(BaseModel):
    """签字请求"""
    signature_url: str


class OrderVerifyRequest(BaseModel):
    """核销请求"""
    verify_status: str  # verified
