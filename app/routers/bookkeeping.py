"""Bookkeeping router - Income/Expense management."""
from datetime import datetime, date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.bookkeeping import BookkeepingRecord
from app.schemas.common import PaginatedResponse, MessageResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff

from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["收支管理"])


class BookkeepingResponse(BaseModel):
    id: UUID
    record_type: str
    category: str
    amount: float
    description: str | None = None
    payment_method: str | None = None
    related_order_id: UUID | None = None
    created_by: UUID | None = None
    record_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class BookkeepingCreate(BaseModel):
    record_type: str = "expense"
    category: str = "other"
    amount: float
    description: str | None = None
    payment_method: str | None = None
    related_order_id: UUID | None = None
    record_date: datetime | None = None


@router.get("/bookkeeping", response_model=PaginatedResponse[BookkeepingResponse])
async def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    record_type: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    query = select(BookkeepingRecord).where(BookkeepingRecord.shop_id.in_(shop_ids))
    if record_type:
        query = query.where(BookkeepingRecord.record_type == record_type)
    if category:
        query = query.where(BookkeepingRecord.category == category)
    if start_date:
        query = query.where(BookkeepingRecord.record_date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.where(BookkeepingRecord.record_date <= datetime.combine(end_date, datetime.max.time()))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(BookkeepingRecord.record_date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[BookkeepingResponse.model_validate(r) for r in records],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("/bookkeeping", response_model=BookkeepingResponse)
async def create_record(
    data: BookkeepingCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    current_staff=Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    record = BookkeepingRecord(
        shop_id=shop_ids[0],
        record_type=data.record_type,
        category=data.category,
        amount=data.amount,
        description=data.description,
        payment_method=data.payment_method,
        related_order_id=data.related_order_id,
        record_date=data.record_date or datetime.utcnow(),
        created_by=current_staff.id if current_staff else None,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return BookkeepingResponse.model_validate(record)


@router.delete("/bookkeeping/{record_id}", response_model=MessageResponse)
async def delete_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BookkeepingRecord).where(BookkeepingRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(record)
    await db.flush()
    return MessageResponse(message="删除成功")
