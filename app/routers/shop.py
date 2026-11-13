"""Shop router - with brand-level data permission."""
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.database import get_db
from app.models.shop import Shop, Room
from app.middleware.auth import get_current_staff, get_effective_shop_ids
from app.models.staff import Staff

router = APIRouter(prefix="/api/shops", tags=["门店管理"])


class ShopCreate(BaseModel):
    name: str
    code: str
    address: str | None = None
    phone: str | None = None
    logo_url: str | None = None


class ShopUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    address: str | None = None
    phone: str | None = None
    logo_url: str | None = None
    is_active: bool | None = None


class ShopResponse(BaseModel):
    id: UUID
    brand_id: UUID | None = None
    name: str
    code: str
    address: str | None = None
    phone: str | None = None
    logo_url: str | None = None
    is_active: bool
    is_deleted: bool = False

    model_config = {"from_attributes": True}


class RoomCreate(BaseModel):
    shop_id: UUID
    name: str
    beds: int = 1
    floor: int | None = None


class RoomUpdate(BaseModel):
    name: str | None = None
    beds: int | None = None
    floor: int | None = None
    is_active: bool | None = None


class RoomResponse(BaseModel):
    id: UUID
    shop_id: UUID | None = None
    name: str
    beds: int
    floor: int | None = None
    is_active: bool

    model_config = {"from_attributes": True}


# ========== Shop CRUD ==========

@router.get("", response_model=list[ShopResponse])
async def list_shops(
    is_active: Optional[bool] = None,
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """List shops - brand-level sees all brand shops, others see own shop only."""
    if staff.is_brand_level:
        # Brand-level: all shops under the brand
        query = select(Shop).where(Shop.brand_id == staff.brand_id)
    else:
        # Shop-level: only own shop
        query = select(Shop).where(Shop.id == staff.shop_id)

    if is_active is not None:
        query = query.where(Shop.is_active == is_active)
    # Always exclude soft-deleted shops
    query = query.where(Shop.is_deleted == False)

    result = await db.execute(query)
    shops = result.scalars().all()
    return [ShopResponse.model_validate(s) for s in shops]


@router.post("", response_model=ShopResponse)
async def create_shop(
    data: ShopCreate,
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new shop (brand-level roles only)."""
    if not staff.is_brand_level:
        raise HTTPException(status_code=403, detail="无权创建门店")

    # Check duplicate code within the brand
    if staff.brand_id:
        existing = (await db.execute(
            select(Shop).where(Shop.brand_id == staff.brand_id, Shop.code == data.code)
        )).scalar_one_or_none()
    else:
        existing = (await db.execute(
            select(Shop).where(Shop.code == data.code)
        )).scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="门店编码已存在")

    shop_data = data.model_dump()
    shop_data["brand_id"] = staff.brand_id
    shop = Shop(**shop_data)
    db.add(shop)
    await db.commit()
    await db.refresh(shop)
    return ShopResponse.model_validate(shop)


@router.get("/{shop_id}", response_model=ShopResponse)
async def get_shop(
    shop_id: UUID,
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get shop detail."""
    result = await db.execute(select(Shop).where(Shop.id == shop_id))
    shop = result.scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="门店不存在")
    # Verify brand access
    if not staff.is_brand_level and shop.id != staff.shop_id:
        raise HTTPException(status_code=403, detail="无权访问该门店")
    return ShopResponse.model_validate(shop)


@router.put("/{shop_id}", response_model=ShopResponse)
async def update_shop(
    shop_id: UUID,
    data: ShopUpdate,
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a shop (brand-level roles only)."""
    if not staff.is_brand_level:
        raise HTTPException(status_code=403, detail="无权编辑门店")

    result = await db.execute(select(Shop).where(Shop.id == shop_id))
    shop = result.scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="门店不存在")
    if shop.brand_id != staff.brand_id:
        raise HTTPException(status_code=403, detail="无权编辑该门店")

    update_data = data.model_dump(exclude_unset=True)
    if "code" in update_data and update_data["code"] != shop.code:
        dup = (await db.execute(
            select(Shop).where(Shop.brand_id == staff.brand_id, Shop.code == update_data["code"], Shop.id != shop_id)
        )).scalar_one_or_none()
        if dup:
            raise HTTPException(status_code=400, detail="门店编码已存在")
    for k, v in update_data.items():
        setattr(shop, k, v)
    await db.commit()
    await db.refresh(shop)
    return ShopResponse.model_validate(shop)


@router.delete("/{shop_id}")
async def delete_shop(
    shop_id: UUID,
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a shop (brand-level roles only, soft delete)."""
    if not staff.is_brand_level:
        raise HTTPException(status_code=403, detail="无权删除门店")

    result = await db.execute(select(Shop).where(Shop.id == shop_id))
    shop = result.scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="门店不存在")
    if shop.brand_id != staff.brand_id:
        raise HTTPException(status_code=403, detail="无权删除该门店")
    shop.is_deleted = True
    shop.is_active = False
    await db.commit()
    return {"message": "门店已删除"}


# ========== Room CRUD ==========

@router.get("/{shop_id}/rooms", response_model=list[RoomResponse])
async def list_rooms(
    shop_id: UUID,
    is_active: Optional[bool] = None,
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """List rooms for a shop."""
    # Verify access to this shop
    if not staff.is_brand_level and shop_id != staff.shop_id:
        raise HTTPException(status_code=403, detail="无权访问该门店")

    query = select(Room).where(Room.shop_id == shop_id)
    if is_active is not None:
        query = query.where(Room.is_active == is_active)
    result = await db.execute(query)
    rooms = result.scalars().all()
    return [RoomResponse.model_validate(r) for r in rooms]


@router.get("/rooms/{room_id}", response_model=RoomResponse)
async def get_room(room_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single room."""
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    return RoomResponse.model_validate(room)


@router.post("/rooms", response_model=RoomResponse)
async def create_room(data: RoomCreate, db: AsyncSession = Depends(get_db)):
    """Create a room."""
    shop = (await db.execute(select(Shop).where(Shop.id == data.shop_id))).scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="门店不存在")
    room = Room(**data.model_dump())
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return RoomResponse.model_validate(room)


@router.put("/rooms/{room_id}", response_model=RoomResponse)
async def update_room(room_id: UUID, data: RoomUpdate, db: AsyncSession = Depends(get_db)):
    """Update a room."""
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(room, k, v)
    await db.commit()
    await db.refresh(room)
    return RoomResponse.model_validate(room)


@router.delete("/rooms/{room_id}")
async def delete_room(room_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a room (soft delete)."""
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    room.is_active = False
    await db.commit()
    return {"message": "房间已删除"}
