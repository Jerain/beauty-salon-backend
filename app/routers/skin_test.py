"""Skin test router - AI skin analysis results CRUD."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.skin_test import SkinTestResult
from app.models.staff import Staff
from app.schemas.skin_test import (
    SkinTestResultResponse, SkinTestResultCreate, SkinTestResultUpdate,
    SkinTestCompareResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api", tags=["AI测肤"])


@router.get("/skin-tests", response_model=PaginatedResponse[SkinTestResultResponse])
async def list_skin_tests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: Optional[UUID] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    query = select(SkinTestResult).where(SkinTestResult.shop_id.in_(shop_ids))
    if customer_id:
        query = query.where(SkinTestResult.customer_id == customer_id)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(SkinTestResult.test_time.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=[SkinTestResultResponse.model_validate(r) for r in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("/skin-tests", response_model=SkinTestResultResponse)
async def create_skin_test(
    data: SkinTestResultCreate,
    current_staff: Staff = Depends(get_current_staff),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    result = SkinTestResult(
        customer_id=data.customer_id, shop_id=shop_ids[0],
        device_id=data.device_id,
        overall_score=data.overall_score, skin_type=data.skin_type,
        pore_score=data.pore_score, pore_count=data.pore_count,
        pore_diameter=data.pore_diameter,
        acne_score=data.acne_score, acne_count=data.acne_count,
        spot_score=data.spot_score, spot_area=data.spot_area,
        wrinkle_score=data.wrinkle_score, wrinkle_count=data.wrinkle_count,
        skin_color_score=data.skin_color_score, skin_brightness=data.skin_brightness,
        moisture_score=data.moisture_score, moisture_index=data.moisture_index,
        sensitive_score=data.sensitive_score, sensitive_level=data.sensitive_level,
        blackhead_score=data.blackhead_score, blackhead_count=data.blackhead_count,
        front_image=data.front_image, left_image=data.left_image, right_image=data.right_image,
        remark=data.remark, report_url=data.report_url,
        operator_id=current_staff.id,
    )
    db.add(result)
    await db.flush()
    await db.refresh(result)
    return SkinTestResultResponse.model_validate(result)


# ============ Static routes (MUST be before {test_id}) ============

@router.get("/skin-tests/search", response_model=list[SkinTestResultResponse])
async def search_skin_tests(
    customer_id: UUID,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SkinTestResult)
        .where(and_(
            SkinTestResult.customer_id == customer_id,
            SkinTestResult.shop_id.in_(shop_ids),
        ))
        .order_by(SkinTestResult.test_time.desc())
    )
    return [SkinTestResultResponse.model_validate(r) for r in result.scalars().all()]


@router.get("/skin-tests/count", response_model=dict)
async def skin_test_count(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(
        select(func.count()).where(SkinTestResult.shop_id.in_(shop_ids))
    )).scalar() or 0
    today = datetime.utcnow().date()
    today_count = (await db.execute(
        select(func.count()).where(and_(
            SkinTestResult.shop_id.in_(shop_ids),
            func.date(SkinTestResult.test_time) == today,
        ))
    )).scalar() or 0
    return {"total": total, "today": today_count}


@router.get("/skin-tests/compare/{before_id}/{after_id}", response_model=SkinTestCompareResponse)
async def compare_skin_tests(
    before_id: UUID, after_id: UUID, db: AsyncSession = Depends(get_db),
):
    r1 = await db.execute(select(SkinTestResult).where(SkinTestResult.id == before_id))
    before = r1.scalar_one_or_none()
    r2 = await db.execute(select(SkinTestResult).where(SkinTestResult.id == after_id))
    after = r2.scalar_one_or_none()
    if not before or not after:
        raise HTTPException(status_code=404, detail="测肤记录不存在")

    dimensions = [
        "pore_score", "acne_score", "spot_score", "wrinkle_score",
        "skin_color_score", "moisture_score", "sensitive_score", "blackhead_score",
        "overall_score",
    ]
    improvements = {}
    for dim in dimensions:
        v1 = getattr(before, dim, None)
        v2 = getattr(after, dim, None)
        if v1 is not None and v2 is not None:
            improvements[dim] = v2 - v1

    return SkinTestCompareResponse(
        before=SkinTestResultResponse.model_validate(before),
        after=SkinTestResultResponse.model_validate(after),
        improvements=improvements,
    )


# ============ Dynamic routes ({test_id}) ============

@router.get("/skin-tests/{test_id}", response_model=SkinTestResultResponse)
async def get_skin_test(test_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SkinTestResult).where(SkinTestResult.id == test_id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="测肤记录不存在")
    return SkinTestResultResponse.model_validate(test)


@router.put("/skin-tests/{test_id}", response_model=SkinTestResultResponse)
async def update_skin_test(
    test_id: UUID, data: SkinTestResultUpdate, db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SkinTestResult).where(SkinTestResult.id == test_id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="测肤记录不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(test, field, value)
    db.add(test)
    await db.flush()
    await db.refresh(test)
    return SkinTestResultResponse.model_validate(test)


@router.delete("/skin-tests/{test_id}", response_model=MessageResponse)
async def delete_skin_test(test_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SkinTestResult).where(SkinTestResult.id == test_id))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="测肤记录不存在")
    await db.delete(test)
    return MessageResponse(message="删除成功")
