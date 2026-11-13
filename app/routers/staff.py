"""Staff router - CRUD for staff and positions."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.staff import Staff, Position
from app.models.shop import Shop
from app.schemas.staff import (
    StaffResponse, StaffCreate, StaffUpdate,
    PositionResponse, PositionCreate, PositionUpdate,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff
import bcrypt

router = APIRouter(prefix="/api", tags=["员工管理"])


def _staff_response(s: Staff) -> StaffResponse:
    pos = getattr(s, "position", None)
    return StaffResponse(
        id=s.id,
        name=s.name,
        phone=s.phone,
        avatar_url=s.avatar_url,
        shop_id=s.shop_id,
        position_id=s.position_id,
        position_name=pos.name if pos else None,
        role=s.role,
        is_active=s.is_active,
        is_on_duty=s.is_on_duty,
        bio=s.bio,
        hire_date=s.hire_date,
        points=s.points,
        created_at=s.created_at,
    )


# ============ Positions ============

@router.get("/positions", response_model=list[PositionResponse])
async def list_positions(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List all positions."""
    result = await db.execute(
        select(Position).where(Position.is_active == True).order_by(Position.sort_order)
    )
    positions = result.scalars().all()
    return [PositionResponse.model_validate(p) for p in positions]


@router.post("/positions", response_model=PositionResponse)
async def create_position(
    data: PositionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new position."""
    position = Position(name=data.name, sort_order=data.sort_order)
    db.add(position)
    await db.flush()
    await db.refresh(position)
    return PositionResponse.model_validate(position)


@router.put("/positions/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: UUID,
    data: PositionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update position."""
    result = await db.execute(
        select(Position).where(Position.id == position_id)
    )
    pos = result.scalar_one_or_none()
    if not pos:
        raise HTTPException(status_code=404, detail="职位不存在")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pos, field, value)
    db.add(pos)
    await db.flush()
    await db.refresh(pos)
    return PositionResponse.model_validate(pos)


@router.delete("/positions/{position_id}", response_model=MessageResponse)
async def delete_position(
    position_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete position."""
    result = await db.execute(
        select(Position).where(Position.id == position_id)
    )
    pos = result.scalar_one_or_none()
    if not pos:
        raise HTTPException(status_code=404, detail="职位不存在")
    pos.is_active = False
    db.add(pos)
    return MessageResponse(message="删除成功")


# ============ Staff ============

@router.get("/staff", response_model=PaginatedResponse[StaffResponse])
async def list_staff(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated staff list with search."""
    query = (
        select(Staff)
        .where(Staff.shop_id.in_(shop_ids), Staff.is_active == True)
        .options(selectinload(Staff.position))
    )

    if search:
        query = query.where(
            func.lower(Staff.name).contains(func.lower(search))
        )
    if role:
        query = query.where(Staff.role == role)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = query.order_by(Staff.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    staff_list = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[_staff_response(s) for s in staff_list],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/staff", response_model=StaffResponse)
async def create_staff(
    data: StaffCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new staff member."""
    staff = Staff(
        name=data.name,
        phone=data.phone,
        password_hash=bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        shop_id=shop_ids[0],
        brand_id=current_staff.brand_id,
        position_id=data.position_id,
        role=data.role,
        hire_date=data.hire_date,
    )
    db.add(staff)
    await db.flush()
    await db.refresh(staff, ["position"])
    return _staff_response(staff)


@router.get("/staff/{staff_id}", response_model=StaffResponse)
async def get_staff(
    staff_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get staff detail."""
    result = await db.execute(
        select(Staff).where(Staff.id == staff_id).options(selectinload(Staff.position))
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="员工不存在")

    return _staff_response(staff)


@router.put("/staff/{staff_id}", response_model=MessageResponse)
async def update_staff(
    staff_id: UUID,
    data: StaffUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update staff info."""
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="员工不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(staff, field, value)

    db.add(staff)
    return MessageResponse(message="更新成功")


@router.delete("/staff/{staff_id}", response_model=MessageResponse)
async def delete_staff(
    staff_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete staff."""
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="员工不存在")

    staff.is_active = False
    db.add(staff)
    return MessageResponse(message="删除成功")


@router.put("/staff/{staff_id}/switch-status", response_model=MessageResponse)
async def switch_staff_status(
    staff_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Toggle staff on-duty status (上架/下架)."""
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="员工不存在")
    staff.is_on_duty = not staff.is_on_duty
    db.add(staff)
    status_text = "上架" if staff.is_on_duty else "下架"
    return MessageResponse(message=f"已{status_text}")


@router.get("/staff/{staff_id}/points", response_model=dict)
async def get_staff_points(
    staff_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get staff points."""
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="员工不存在")
    return {"staff_id": str(staff.id), "staff_name": staff.name, "points": staff.points}


@router.put("/staff/{staff_id}/points", response_model=MessageResponse)
async def update_staff_points(
    staff_id: UUID,
    points: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Update staff points."""
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="员工不存在")
    staff.points += points
    db.add(staff)
    return MessageResponse(message="积分更新成功")
