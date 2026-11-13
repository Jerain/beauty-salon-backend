"""Commission router - rules, calculation, records, performance."""
from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.commission import CommissionRule, CommissionRecord
from app.models.staff import Staff
from app.models.order import Order, OrderItem
from app.models.card import CardTransaction
from app.schemas.commission import (
    CommissionRuleResponse, CommissionRuleCreate, CommissionRuleUpdate,
    CommissionRecordResponse, CalcCommissionRequest, CalcCommissionResponse,
    StaffPerformanceResponse,
)
from app.schemas.common import MessageResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api", tags=["提成管理"])


def _rule_response(r: CommissionRule) -> CommissionRuleResponse:
    return CommissionRuleResponse(
        id=r.id,
        name=r.name,
        rule_type=r.rule_type,
        commission_rate=float(r.commission_rate) if r.commission_rate else None,
        commission_amount=float(r.commission_amount) if r.commission_amount else None,
        step_rules=r.step_rules,
        shop_id=r.shop_id,
        is_active=r.is_active,
        created_at=r.created_at,
    )


def _record_response(r: CommissionRecord) -> CommissionRecordResponse:
    stf = getattr(r, "staff", None)
    return CommissionRecordResponse(
        id=r.id,
        staff_id=r.staff_id,
        staff_name=stf.name if stf else None,
        order_id=r.order_id,
        commission_rule_id=r.commission_rule_id,
        commission_type=r.commission_type,
        base_amount=float(r.base_amount),
        commission_rate=float(r.commission_rate),
        commission_amount=float(r.commission_amount),
        month=r.month,
        created_at=r.created_at,
    )


# ============ Commission Rules ============

@router.get("/commission/rules", response_model=list[CommissionRuleResponse])
async def list_commission_rules(
    rule_type: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List commission rules."""
    query = select(CommissionRule).where(CommissionRule.shop_id.in_(shop_ids))
    if rule_type:
        query = query.where(CommissionRule.rule_type == rule_type)
    query = query.order_by(CommissionRule.created_at.desc())
    result = await db.execute(query)
    rules = result.scalars().all()
    return [_rule_response(r) for r in rules]


@router.post("/commission/rules", response_model=CommissionRuleResponse)
async def create_commission_rule(
    data: CommissionRuleCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a commission rule."""
    rule = CommissionRule(
        name=data.name,
        rule_type=data.rule_type,
        commission_rate=data.commission_rate,
        commission_amount=data.commission_amount,
        step_rules=data.step_rules,
        shop_id=shop_ids[0],
    )
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return _rule_response(rule)


@router.get("/commission/rules/{rule_id}", response_model=CommissionRuleResponse)
async def get_commission_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get commission rule detail."""
    result = await db.execute(
        select(CommissionRule).where(CommissionRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="提成规则不存在")
    return _rule_response(rule)


@router.put("/commission/rules/{rule_id}", response_model=CommissionRuleResponse)
async def update_commission_rule(
    rule_id: UUID,
    data: CommissionRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update commission rule."""
    result = await db.execute(
        select(CommissionRule).where(CommissionRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="提成规则不存在")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return _rule_response(rule)


@router.delete("/commission/rules/{rule_id}", response_model=MessageResponse)
async def delete_commission_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete commission rule (soft)."""
    result = await db.execute(
        select(CommissionRule).where(CommissionRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="提成规则不存在")
    rule.is_active = False
    db.add(rule)
    return MessageResponse(message="删除成功")


# ============ Commission Calculation ============

@router.post("/commission/calc-staff-commission", response_model=CalcCommissionResponse)
async def calc_staff_commission(
    data: CalcCommissionRequest,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Calculate commission for a staff member."""
    # Find matching rule
    result = await db.execute(
        select(CommissionRule).where(
            and_(
                CommissionRule.rule_type == data.commission_type,
                CommissionRule.shop_id.in_(shop_ids),
                CommissionRule.is_active == True,
            )
        )
    )
    rule = result.scalars().first()
    if not rule:
        return CalcCommissionResponse(
            commission_amount=0.0,
            commission_rate=0.0,
            rule_name=None,
        )

    commission_amount = 0.0
    commission_rate = 0.0

    if rule.rule_type == "step" and rule.step_rules:
        # Step commission: find the right bracket
        for step in sorted(rule.step_rules, key=lambda x: x.get("min", 0)):
            if step.get("min", 0) <= data.base_amount < step.get("max", float("inf")):
                commission_rate = step.get("rate", 0)
                commission_amount = data.base_amount * commission_rate / 100
                break
    elif rule.commission_rate:
        commission_rate = float(rule.commission_rate)
        commission_amount = data.base_amount * commission_rate / 100
    elif rule.commission_amount:
        commission_amount = float(rule.commission_amount)

    return CalcCommissionResponse(
        commission_amount=round(commission_amount, 2),
        commission_rate=commission_rate,
        rule_name=rule.name,
    )


# ============ Commission Records ============

@router.get("/commission/records", response_model=list[CommissionRecordResponse])
async def list_commission_records(
    staff_id: Optional[UUID] = None,
    month: Optional[str] = None,
    commission_type: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List commission records."""
    query = (
        select(CommissionRecord)
        .join(Staff, CommissionRecord.staff_id == Staff.id)
        .where(Staff.shop_id.in_(shop_ids))
        .options(selectinload(CommissionRecord.staff))
    )
    if staff_id:
        query = query.where(CommissionRecord.staff_id == staff_id)
    if month:
        query = query.where(CommissionRecord.month == month)
    if commission_type:
        query = query.where(CommissionRecord.commission_type == commission_type)
    query = query.order_by(CommissionRecord.created_at.desc())
    result = await db.execute(query)
    records = result.scalars().all()
    return [_record_response(r) for r in records]


@router.post("/commission/records", response_model=CommissionRecordResponse)
async def create_commission_record(
    staff_id: UUID,
    order_id: UUID,
    commission_type: str,
    base_amount: float,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create commission record (typically called after order completion)."""
    # Calculate commission
    result = await db.execute(
        select(CommissionRule).where(
            and_(
                CommissionRule.rule_type == commission_type,
                CommissionRule.shop_id.in_(shop_ids),
                CommissionRule.is_active == True,
            )
        )
    )
    rule = result.scalars().first()

    commission_amount = 0.0
    commission_rate = 0.0

    if rule:
        if rule.rule_type == "step" and rule.step_rules:
            for step in sorted(rule.step_rules, key=lambda x: x.get("min", 0)):
                if step.get("min", 0) <= base_amount < step.get("max", float("inf")):
                    commission_rate = step.get("rate", 0)
                    commission_amount = base_amount * commission_rate / 100
                    break
        elif rule.commission_rate:
            commission_rate = float(rule.commission_rate)
            commission_amount = base_amount * commission_rate / 100
        elif rule.commission_amount:
            commission_amount = float(rule.commission_amount)

    month = datetime.utcnow().strftime("%Y-%m")
    record = CommissionRecord(
        staff_id=staff_id,
        order_id=order_id,
        commission_rule_id=rule.id if rule else None,
        commission_type=commission_type,
        base_amount=base_amount,
        commission_rate=commission_rate,
        commission_amount=round(commission_amount, 2),
        month=month,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record, ["staff"])
    return _record_response(record)


# ============ Staff Performance Report ============

@router.get("/report/staff-data/list", response_model=list[StaffPerformanceResponse])
async def staff_performance_list(
    month: str = Query(..., description="YYYY-MM"),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get staff performance summary for a month."""
    staff_result = await db.execute(
        select(Staff).where(and_(Staff.shop_id.in_(shop_ids), Staff.is_active == True))
    )
    staff_list = staff_result.scalars().all()

    year, mon = int(month[:4]), int(month[5:7])
    first_day = date(year, mon, 1)
    if mon == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, mon + 1, 1) - timedelta(days=1)

    perf_list = []
    for s in staff_list:
        # Commission records
        comm_result = await db.execute(
            select(
                func.coalesce(func.sum(CommissionRecord.commission_amount), 0),
            ).where(
                and_(
                    CommissionRecord.staff_id == s.id,
                    CommissionRecord.month == month,
                )
            )
        )
        total_commission = float(comm_result.scalar() or 0)

        # Orders where staff participated (as order items' service staff)
        order_result = await db.execute(
            select(
                func.coalesce(func.sum(Order.total_amount), 0),
                func.count(func.distinct(Order.id)),
            )
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(
                and_(
                    OrderItem.staff_id == s.id,
                    Order.created_at >= datetime(year, mon, 1),
                    Order.created_at < (datetime(year, mon + 1, 1) if mon < 12 else datetime(year + 1, 1, 1)),
                )
            )
        )
        order_row = order_result.one()
        total_revenue = float(order_row[0] or 0)
        service_count = int(order_row[1] or 0)

        # Card recharge - simplified
        recharge_amount = 0.0

        perf_list.append(StaffPerformanceResponse(
            staff_id=s.id,
            staff_name=s.name,
            total_revenue=total_revenue,
            service_count=service_count,
            recharge_amount=recharge_amount,
            card_consume_amount=0.0,
            total_commission=total_commission,
            month=month,
        ))
    return perf_list


@router.get("/report/staff-data/orders", response_model=list)
async def staff_performance_orders(
    staff_id: UUID,
    month: str = Query(..., description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
):
    """Get orders for a specific staff in a month."""
    year, mon = int(month[:4]), int(month[5:7])
    result = await db.execute(
        select(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(
            and_(
                OrderItem.staff_id == staff_id,
                Order.created_at >= datetime(year, mon, 1),
                Order.created_at < datetime(year, mon + 1, 1) if mon < 12 else datetime(year + 1, 1, 1),
            )
        )
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().unique().all()
    return [
        {
            "id": str(o.id),
            "order_no": o.order_no,
            "total_amount": float(o.total_amount),
            "status": o.status,
            "created_at": o.created_at.isoformat(),
        }
        for o in orders
    ]
