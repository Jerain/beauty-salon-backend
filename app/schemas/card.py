"""Card (CardType/MemberCard/CardTransaction) schemas."""
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.types import BrowserDatetime


# ============ CardType ============

class CardTypeResponse(BaseModel):
    id: UUID
    name: str
    card_category: str  # stored_value/times/period/discount/point/package
    sell_price: float
    face_value: float
    present_amount: float = 0.0
    present_items: list | None = None
    validity_type: str = "permanent"  # permanent/fixed/days
    validity_days: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    consume_rule: dict | None = None
    applicable_shops: list[str] | None = None
    description: str | None = None
    shop_id: UUID | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CardTypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=30)
    card_category: str  # stored_value/times/period/discount/point/package
    sell_price: float = Field(..., ge=0)
    face_value: float = Field(..., gt=0)
    present_amount: float = 0.0
    present_items: list | None = None
    validity_type: str = "permanent"
    validity_days: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    consume_rule: dict | None = None
    applicable_shops: list[str] | None = None
    description: str | None = None


class CardTypeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=30)
    card_category: str | None = None
    sell_price: float | None = Field(None, ge=0)
    face_value: float | None = Field(None, gt=0)
    present_amount: float | None = None
    present_items: list | None = None
    validity_type: str | None = None
    validity_days: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    consume_rule: dict | None = None
    applicable_shops: list[str] | None = None
    description: str | None = None


# ============ MemberCard ============

class MemberCardResponse(BaseModel):
    id: UUID
    customer_id: UUID
    customer_name: str | None = None
    card_type_id: UUID
    card_type_name: str | None = None
    card_category: str | None = None
    card_no: str
    principal_balance: float
    present_balance: float
    total_times: int | None = None
    remaining_times: int | None = None
    status: str
    activate_date: datetime
    expire_date: datetime | None = None
    remark: str | None = None
    shop_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberCardCreate(BaseModel):
    """开卡：设置本金/赠金/次数/有效期"""
    customer_id: UUID
    card_type_id: UUID
    card_no: str | None = None  # 可自动生成
    principal_amount: float = 0.0  # 本金（储值卡）
    present_amount: float = 0.0  # 赠金
    total_times: int | None = None  # 总次数（次卡）
    expire_date: BrowserDatetime | None = None  # 有效期
    remark: str | None = None


class MemberCardRecharge(BaseModel):
    """充值"""
    amount: float = Field(..., gt=0)  # 本金充值
    present_amount: float = 0.0  # 赠送金额
    payment_method: str = "cash"  # cash/wechat/alipay/card
    remark: str | None = None


class MemberCardBalanceAdjust(BaseModel):
    """余额调整（手动）"""
    principal_change: float = 0.0
    present_change: float = 0.0
    times_change: int = 0
    remark: str | None = None


class MemberCardFreeze(BaseModel):
    """冻结/解冻"""
    action: str  # freeze / unfreeze
    remark: str | None = None


class MemberCardDelay(BaseModel):
    """卡延期"""
    days: int = Field(..., gt=0)  # 延长天数
    remark: str | None = None


class MemberCardTransfer(BaseModel):
    """卡转赠"""
    target_customer_id: UUID  # 接收方顾客ID
    remark: str | None = None


class MemberCardRemark(BaseModel):
    """卡备注"""
    remark: str


class MemberCardRefund(BaseModel):
    """退卡"""
    reason: str | None = None


class MemberCardConsume(BaseModel):
    """卡消费（由收银台调用）"""
    amount: float = 0.0  # 消费金额
    times: int = 0  # 消费次数
    order_id: UUID | None = None
    remark: str | None = None


# ============ CardTransaction ============

class CardTransactionResponse(BaseModel):
    id: UUID
    member_card_id: UUID
    customer_id: UUID
    order_id: UUID | None = None
    transaction_type: str  # consume/recharge/adjust/refund/gift/activate/transfer
    principal_change: float
    present_change: float
    times_change: int | None = None
    before_principal: float
    after_principal: float
    before_present: float
    after_present: float
    before_times: int | None = None
    after_times: int | None = None
    operator_id: UUID | None = None
    remark: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
