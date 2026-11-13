"""Report router - business analytics and data analysis."""
from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.order import Order, OrderItem
from app.models.customer import Customer
from app.models.card import MemberCard, CardTransaction, CardType
from app.models.staff import Staff
from app.models.appointment import Appointment
from app.models.commission import CommissionRecord
from app.schemas.common import MessageResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api", tags=["报表分析"])


# ============ Business Overview ============

@router.get("/report/business/overview")
async def business_overview(
    start_date: date = Query(...),
    end_date: date = Query(...),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Business overview for dashboard."""
    # Total revenue
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0))
        .where(and_(
            Order.shop_id.in_(shop_ids),
            Order.status == "completed",
            Order.created_at >= datetime.combine(start_date, datetime.min.time()),
            Order.created_at <= datetime.combine(end_date, datetime.max.time()),
        ))
    )
    total_revenue = float(revenue_result.scalar() or 0)

    # Order count
    order_count_result = await db.execute(
        select(func.count(Order.id))
        .where(and_(
            Order.shop_id.in_(shop_ids),
            Order.status == "completed",
            Order.created_at >= datetime.combine(start_date, datetime.min.time()),
            Order.created_at <= datetime.combine(end_date, datetime.max.time()),
        ))
    )
    order_count = order_count_result.scalar() or 0

    # New customers
    new_customer_result = await db.execute(
        select(func.count(Customer.id))
        .where(and_(
            Customer.shop_id.in_(shop_ids),
            Customer.created_at >= datetime.combine(start_date, datetime.min.time()),
            Customer.created_at <= datetime.combine(end_date, datetime.max.time()),
        ))
    )
    new_customers = new_customer_result.scalar() or 0

    # Average order value
    avg_order = total_revenue / order_count if order_count > 0 else 0.0

    # Recharge amount
    recharge_result = await db.execute(
        select(func.coalesce(func.sum(CardTransaction.principal_change), 0))
        .where(and_(
            CardTransaction.transaction_type == "recharge",
            CardTransaction.created_at >= datetime.combine(start_date, datetime.min.time()),
            CardTransaction.created_at <= datetime.combine(end_date, datetime.max.time()),
        ))
    )
    recharge_amount = float(recharge_result.scalar() or 0)

    # Appointment count
    appt_result = await db.execute(
        select(func.count(Appointment.id))
        .where(and_(
            Appointment.shop_id.in_(shop_ids),
            Appointment.status == "completed",
            Appointment.created_at >= datetime.combine(start_date, datetime.min.time()),
            Appointment.created_at <= datetime.combine(end_date, datetime.max.time()),
        ))
    )
    appointment_count = appt_result.scalar() or 0

    return {
        "total_revenue": round(total_revenue, 2),
        "order_count": order_count,
        "new_customers": new_customers,
        "avg_order_value": round(avg_order, 2),
        "recharge_amount": round(recharge_amount, 2),
        "appointment_count": appointment_count,
    }


# ============ Revenue Report ============

@router.get("/report/revenue/summary")
async def revenue_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    group_by: str = Query("day", description="day/week/month"),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Revenue summary grouped by day/week/month."""
    if group_by == "day":
        date_trunc = func.date_trunc("day", Order.created_at)
    elif group_by == "week":
        date_trunc = func.date_trunc("week", Order.created_at)
    else:
        date_trunc = func.date_trunc("month", Order.created_at)

    result = await db.execute(
        select(
            date_trunc.label("period"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.count(Order.id).label("order_count"),
        )
        .where(and_(
            Order.shop_id.in_(shop_ids),
            Order.status == "completed",
            Order.created_at >= datetime.combine(start_date, datetime.min.time()),
            Order.created_at <= datetime.combine(end_date, datetime.max.time()),
        ))
        .group_by(date_trunc)
        .order_by(date_trunc)
    )
    rows = result.all()
    return [
        {
            "period": str(r.period)[:10] if r.period else "",
            "revenue": float(r.revenue),
            "order_count": r.order_count,
        }
        for r in rows
    ]


@router.get("/report/revenue/detail")
async def revenue_detail(
    start_date: date = Query(...),
    end_date: date = Query(...),
    payment_method: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Revenue detail by payment method."""
    from app.models.order import Payment
    query = (
        select(
            Payment.payment_method_name,
            func.coalesce(func.sum(Payment.amount), 0).label("total"),
            func.count(Payment.id).label("count"),
        )
        .join(Order, Payment.order_id == Order.id)
        .where(and_(
            Order.shop_id.in_(shop_ids),
            Order.created_at >= datetime.combine(start_date, datetime.min.time()),
            Order.created_at <= datetime.combine(end_date, datetime.max.time()),
        ))
    )
    if payment_method:
        query = query.where(Payment.payment_method_name == payment_method)
    query = query.group_by(Payment.payment_method_name)
    result = await db.execute(query)
    return [
        {
            "payment_method": r.payment_method_name,
            "total": float(r.total),
            "count": r.count,
        }
        for r in result.all()
    ]


# ============ Customer Report ============

@router.get("/report/business/customer")
async def customer_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Customer analytics report."""
    # Total customers
    total = (await db.execute(
        select(func.count(Customer.id)).where(Customer.shop_id.in_(shop_ids))
    )).scalar() or 0

    # New customers in period
    new_customers = (await db.execute(
        select(func.count(Customer.id)).where(and_(
            Customer.shop_id.in_(shop_ids),
            Customer.created_at >= datetime.combine(start_date, datetime.min.time()),
            Customer.created_at <= datetime.combine(end_date, datetime.max.time()),
        ))
    )).scalar() or 0

    # Active customers (with orders in period)
    active = (await db.execute(
        select(func.count(func.distinct(Order.customer_id))).where(and_(
            Order.shop_id.in_(shop_ids),
            Order.status == "completed",
            Order.created_at >= datetime.combine(start_date, datetime.min.time()),
            Order.created_at <= datetime.combine(end_date, datetime.max.time()),
        ))
    )).scalar() or 0

    # Source distribution - join with Source table
    from app.models.customer import Source
    source_result = await db.execute(
        select(
            Source.name, func.count(Customer.id).label("count")
        ).join(Customer, Customer.source_id == Source.id, isouter=True)
        .where(Customer.shop_id.in_(shop_ids))
        .group_by(Source.name)
    )
    source_dist = [{"source": r.name or "未知", "count": r.count} for r in source_result.all()]

    return {
        "total_customers": total,
        "new_customers": new_customers,
        "active_customers": active,
        "source_distribution": source_dist,
    }


# ============ Staff Performance Report ============

@router.get("/report/staff-performance")
async def staff_performance_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Staff performance summary."""
    staff_result = await db.execute(
        select(Staff).where(and_(Staff.shop_id.in_(shop_ids), Staff.is_active == True))
    )
    staff_list = staff_result.scalars().all()

    perf = []
    for s in staff_list:
        comm = (await db.execute(
            select(func.coalesce(func.sum(CommissionRecord.commission_amount), 0))
            .where(and_(
                CommissionRecord.staff_id == s.id,
                CommissionRecord.created_at >= datetime.combine(start_date, datetime.min.time()),
                CommissionRecord.created_at <= datetime.combine(end_date, datetime.max.time()),
            ))
        )).scalar() or 0

        perf.append({
            "staff_id": str(s.id),
            "staff_name": s.name,
            "total_commission": float(comm),
        })
    return perf


# ============ Card Consumption Report ============

@router.get("/report/card-consumption")
async def card_consumption_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Card consumption analytics."""
    # Total card consume
    consume_result = await db.execute(
        select(
            func.coalesce(func.sum(CardTransaction.principal_change), 0),
            func.count(CardTransaction.id),
        ).where(and_(
            CardTransaction.transaction_type == "consume",
            CardTransaction.created_at >= datetime.combine(start_date, datetime.min.time()),
            CardTransaction.created_at <= datetime.combine(end_date, datetime.max.time()),
        ))
    )
    consume_row = consume_result.one()

    # Total recharge
    recharge_result = await db.execute(
        select(
            func.coalesce(func.sum(CardTransaction.principal_change), 0),
            func.count(CardTransaction.id),
        ).where(and_(
            CardTransaction.transaction_type == "recharge",
            CardTransaction.created_at >= datetime.combine(start_date, datetime.min.time()),
            CardTransaction.created_at <= datetime.combine(end_date, datetime.max.time()),
        ))
    )
    recharge_row = recharge_result.one()

    # New cards
    new_cards = (await db.execute(
        select(func.count(MemberCard.id)).where(and_(
            MemberCard.created_at >= datetime.combine(start_date, datetime.min.time()),
            MemberCard.created_at <= datetime.combine(end_date, datetime.max.time()),
        ))
    )).scalar() or 0

    return {
        "consume_amount": float(consume_row[0] or 0),
        "consume_count": consume_row[1] or 0,
        "recharge_amount": float(recharge_row[0] or 0),
        "recharge_count": recharge_row[1] or 0,
        "new_cards": new_cards,
    }


# ============ Business Preview / KPI ============

@router.get("/report/business-preview/collect")
async def business_preview(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Quick KPI overview for today."""
    today = date.today()
    first_of_month = today.replace(day=1)

    # Today revenue
    today_rev = (await db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0))
        .where(and_(
            Order.shop_id.in_(shop_ids),
            Order.status == "completed",
            func.date(Order.created_at) == today,
        ))
    )).scalar() or 0

    # Month revenue
    month_rev = (await db.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0))
        .where(and_(
            Order.shop_id.in_(shop_ids),
            Order.status == "completed",
            Order.created_at >= datetime.combine(first_of_month, datetime.min.time()),
        ))
    )).scalar() or 0

    # Today appointments
    today_appt = (await db.execute(
        select(func.count(Appointment.id))
        .where(and_(
            Appointment.shop_id.in_(shop_ids),
            Appointment.appointment_date == today,
        ))
    )).scalar() or 0

    # Total customers
    total_cust = (await db.execute(
        select(func.count(Customer.id)).where(Customer.shop_id.in_(shop_ids))
    )).scalar() or 0

    return {
        "today_revenue": float(today_rev),
        "month_revenue": float(month_rev),
        "today_appointments": today_appt,
        "total_customers": total_cust,
    }
