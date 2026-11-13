"""Commission schemas."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class CommissionRuleResponse(BaseModel):
    id: UUID
    name: str
    rule_type: str  # service/sales/recharge/step
    commission_rate: float | None = None
    commission_amount: float | None = None
    step_rules: list | None = None
    shop_id: UUID | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CommissionRuleCreate(BaseModel):
    name: str
    rule_type: str  # service/sales/recharge/step
    commission_rate: float | None = None
    commission_amount: float | None = None
    step_rules: list | None = None


class CommissionRuleUpdate(BaseModel):
    name: str | None = None
    commission_rate: float | None = None
    commission_amount: float | None = None
    step_rules: list | None = None
    is_active: bool | None = None


class CommissionRecordResponse(BaseModel):
    id: UUID
    staff_id: UUID
    staff_name: str | None = None
    order_id: UUID | None = None
    commission_rule_id: UUID | None = None
    commission_type: str
    base_amount: float
    commission_rate: float
    commission_amount: float
    month: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CalcCommissionRequest(BaseModel):
    staff_id: UUID
    order_id: UUID | None = None
    commission_type: str  # service/sales/recharge
    base_amount: float


class CalcCommissionResponse(BaseModel):
    commission_amount: float
    commission_rate: float
    rule_name: str | None = None


class StaffPerformanceResponse(BaseModel):
    staff_id: UUID
    staff_name: str | None = None
    total_revenue: float = 0.0
    service_count: int = 0
    recharge_amount: float = 0.0
    card_consume_amount: float = 0.0
    total_commission: float = 0.0
    month: str
