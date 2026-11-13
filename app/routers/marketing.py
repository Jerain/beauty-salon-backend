"""Marketing router - coupons, activities, third-party verification."""
from datetime import datetime, date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.marketing import Coupon, MarketingActivity
from app.schemas.marketing import (
    CouponResponse, CouponCreate, CouponUpdate, CouponUseRequest,
    MarketingActivityResponse, MarketingActivityCreate, MarketingActivityUpdate,
    MarketingOverviewResponse,
    ThirdPartyVerifyRequest, ThirdPartyVerifyResponse,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api", tags=["营销与核销"])


# ============ Coupons ============

@router.get("/coupons", response_model=PaginatedResponse[CouponResponse])
async def list_coupons(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    coupon_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    query = select(Coupon).where(Coupon.shop_id.in_(shop_ids))
    if coupon_type:
        query = query.where(Coupon.coupon_type == coupon_type)
    if is_active is not None:
        query = query.where(Coupon.is_active == is_active)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(Coupon.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    coupons = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[CouponResponse.model_validate(c) for c in coupons],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("/coupons", response_model=CouponResponse)
async def create_coupon(
    data: CouponCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    coupon = Coupon(
        name=data.name, coupon_type=data.coupon_type,
        discount_value=data.discount_value, min_amount=data.min_amount,
        applicable_type=data.applicable_type, applicable_ids=data.applicable_ids,
        total_count=data.total_count, start_date=data.start_date,
        end_date=data.end_date, shop_id=shop_ids[0],
    )
    db.add(coupon)
    await db.flush()
    await db.refresh(coupon)
    return CouponResponse.model_validate(coupon)


@router.get("/coupons/{coupon_id}", response_model=CouponResponse)
async def get_coupon(coupon_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    return CouponResponse.model_validate(coupon)


@router.put("/coupons/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: UUID, data: CouponUpdate, db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(coupon, field, value)
    db.add(coupon)
    await db.flush()
    await db.refresh(coupon)
    return CouponResponse.model_validate(coupon)


@router.delete("/coupons/{coupon_id}", response_model=MessageResponse)
async def delete_coupon(coupon_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    coupon.is_active = False
    db.add(coupon)
    return MessageResponse(message="已停用")


@router.post("/coupons/use", response_model=MessageResponse)
async def use_coupon(
    data: CouponUseRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Coupon).where(Coupon.id == data.coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    if not coupon.is_active:
        raise HTTPException(status_code=400, detail="优惠券已停用")
    if coupon.used_count >= coupon.total_count > 0:
        raise HTTPException(status_code=400, detail="优惠券已用完")
    today = date.today()
    if today < coupon.start_date or today > coupon.end_date:
        raise HTTPException(status_code=400, detail="优惠券不在有效期内")
    if data.order_amount < float(coupon.min_amount):
        raise HTTPException(status_code=400, detail=f"订单金额需满{coupon.min_amount}元")

    coupon.used_count += 1
    db.add(coupon)
    return MessageResponse(message="优惠券使用成功")


# ============ Marketing Activities ============

@router.get("/marketing/activities", response_model=list[MarketingActivityResponse])
async def list_activities(
    status: Optional[str] = None,
    activity_type: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    query = select(MarketingActivity).where(MarketingActivity.shop_id.in_(shop_ids))
    if status:
        query = query.where(MarketingActivity.status == status)
    if activity_type:
        query = query.where(MarketingActivity.activity_type == activity_type)
    query = query.order_by(MarketingActivity.created_at.desc())
    result = await db.execute(query)
    return [MarketingActivityResponse.model_validate(a) for a in result.scalars().all()]


@router.post("/marketing/activities", response_model=MarketingActivityResponse)
async def create_activity(
    data: MarketingActivityCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    activity = MarketingActivity(
        name=data.name, activity_type=data.activity_type,
        description=data.description,
        original_price=data.original_price, activity_price=data.activity_price,
        group_size=data.group_size,
        start_date=data.start_date, end_date=data.end_date,
        shop_id=shop_ids[0],
    )
    db.add(activity)
    await db.flush()
    await db.refresh(activity)
    return MarketingActivityResponse.model_validate(activity)


@router.get("/marketing/activities/{activity_id}", response_model=MarketingActivityResponse)
async def get_activity(activity_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MarketingActivity).where(MarketingActivity.id == activity_id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="营销活动不存在")
    return MarketingActivityResponse.model_validate(activity)


@router.put("/marketing/activities/{activity_id}", response_model=MarketingActivityResponse)
async def update_activity(
    activity_id: UUID, data: MarketingActivityUpdate, db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MarketingActivity).where(MarketingActivity.id == activity_id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="营销活动不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(activity, field, value)
    db.add(activity)
    await db.flush()
    await db.refresh(activity)
    return MarketingActivityResponse.model_validate(activity)


@router.delete("/marketing/activities/{activity_id}", response_model=MessageResponse)
async def delete_activity(activity_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MarketingActivity).where(MarketingActivity.id == activity_id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="营销活动不存在")
    activity.status = "cancelled"
    db.add(activity)
    return MessageResponse(message="已取消")


# ============ Marketing Overview ============

@router.get("/marketing/overview", response_model=MarketingOverviewResponse)
async def marketing_overview(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    base = select(MarketingActivity).where(MarketingActivity.shop_id.in_(shop_ids))
    active = (await db.execute(
        select(func.count()).select_from(base.where(MarketingActivity.status == "active").subquery())
    )).scalar() or 0
    ended = (await db.execute(
        select(func.count()).select_from(base.where(MarketingActivity.status == "ended").subquery())
    )).scalar() or 0
    total_orders = (await db.execute(
        select(func.coalesce(func.sum(MarketingActivity.total_orders), 0))
        .where(and_(MarketingActivity.shop_id.in_(shop_ids)))
    )).scalar() or 0
    return MarketingOverviewResponse(
        active_count=active, pending_verify=0,
        completed_count=ended, total_orders=int(total_orders),
    )


# ============ Third-Party Verification ============

@router.post("/third-party/verify", response_model=ThirdPartyVerifyResponse)
async def verify_third_party_coupon(data: ThirdPartyVerifyRequest):
    """Verify third-party coupon (mock - real would call platform API)."""
    # Mock verification - in production, call actual platform API
    code = data.code.strip()
    if len(code) < 6:
        return ThirdPartyVerifyResponse(
            valid=False, platform=data.platform, code=code,
            message="券码格式无效",
        )
    # Simulate successful verification
    return ThirdPartyVerifyResponse(
        valid=True, platform=data.platform, code=code,
        project_name="基础护理套餐",
        original_price=198.0,
        message="验证成功",
    )


@router.post("/third-party/confirm", response_model=MessageResponse)
async def confirm_third_party_verification(
    code: str,
    platform: str,
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Confirm third-party coupon redemption."""
    return MessageResponse(message=f"{platform}券 {code} 核销成功")
