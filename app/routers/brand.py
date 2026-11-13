"""Brand management router - CRUD for brand enterprises."""
import uuid as _uuid
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.database import get_db
from app.models.brand import Brand
from app.models.shop import Shop
from app.models.staff import Staff
from app.schemas.common import PaginatedResponse, MessageResponse
from app.middleware.auth import get_current_staff
import bcrypt

router = APIRouter(prefix="/api/brands", tags=["品牌管理"])


# ============ Schemas ============

class BrandCreate(BaseModel):
    name: str
    code: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    logo_url: str | None = None
    # First shop (flagship) info
    shop_name: str | None = None
    shop_code: str | None = None
    shop_address: str | None = None
    shop_phone: str | None = None
    # Super admin account
    admin_name: str = "超级管理员"
    admin_phone: str | None = None
    admin_password: str = "123456"


class BrandUpdate(BaseModel):
    name: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    logo_url: str | None = None
    is_active: bool | None = None


class BrandResponse(BaseModel):
    id: UUID
    name: str
    code: str
    contact_name: str | None = None
    contact_phone: str | None = None
    logo_url: str | None = None
    is_active: bool
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class BrandDetailResponse(BrandResponse):
    shop_count: int = 0
    staff_count: int = 0


# ============ CRUD ============

@router.get("", response_model=list[BrandResponse])
async def list_brands(
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """List brands (super_admin sees all, others see own brand)."""
    if staff.is_brand_level:
        query = select(Brand).where(Brand.is_active == True)
    else:
        query = select(Brand).where(Brand.id == staff.brand_id)

    result = await db.execute(query)
    brands = result.scalars().all()
    return [
        BrandResponse(
            id=b.id, name=b.name, code=b.code,
            contact_name=b.contact_name, contact_phone=b.contact_phone,
            logo_url=b.logo_url, is_active=b.is_active,
            created_at=b.created_at.isoformat() if b.created_at else None,
        )
        for b in brands
    ]


@router.get("/{brand_id}", response_model=BrandDetailResponse)
async def get_brand(
    brand_id: UUID,
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get brand detail with statistics."""
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")

    # Verify access
    if not staff.is_brand_level and staff.brand_id != brand_id:
        raise HTTPException(status_code=403, detail="无权访问该品牌")

    # Count shops and staff
    shop_count = (await db.execute(
        select(func.count()).select_from(Shop).where(Shop.brand_id == brand_id, Shop.is_active == True)
    )).scalar() or 0
    staff_count = (await db.execute(
        select(func.count()).select_from(Staff).where(Staff.brand_id == brand_id, Staff.is_active == True)
    )).scalar() or 0

    return BrandDetailResponse(
        id=brand.id, name=brand.name, code=brand.code,
        contact_name=brand.contact_name, contact_phone=brand.contact_phone,
        logo_url=brand.logo_url, is_active=brand.is_active,
        created_at=brand.created_at.isoformat() if brand.created_at else None,
        shop_count=shop_count, staff_count=staff_count,
    )


@router.post("", response_model=BrandDetailResponse)
async def create_brand(
    data: BrandCreate,
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new brand enterprise with flagship shop and super admin account.

    Only super_admin can create new brands.
    """
    if not staff.is_brand_level:
        raise HTTPException(status_code=403, detail="无权创建品牌")

    # Generate code if not provided
    code = data.code or f"BR{_uuid.uuid4().hex[:6].upper()}"

    # Check duplicate code
    existing = (await db.execute(select(Brand).where(Brand.code == code))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="品牌编码已存在")

    # 1. Create brand
    brand = Brand(
        name=data.name,
        code=code,
        contact_name=data.contact_name,
        contact_phone=data.contact_phone,
        logo_url=data.logo_url,
    )
    db.add(brand)
    await db.flush()

    # 2. Create flagship shop
    shop_code = data.shop_code or f"S{code}01"
    shop = Shop(
        brand_id=brand.id,
        name=data.shop_name or f"{data.name}旗舰店",
        code=shop_code,
        address=data.shop_address,
        phone=data.shop_phone,
    )
    db.add(shop)
    await db.flush()

    # 3. Create super admin account
    admin_phone = data.admin_phone or f"138{_uuid.uuid4().hex[:8]}"
    password_hash = bcrypt.hashpw(data.admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    admin = Staff(
        brand_id=brand.id,
        shop_id=shop.id,
        name=data.admin_name,
        phone=admin_phone,
        password_hash=password_hash,
        role=Staff.ROLE_SUPER_ADMIN,
    )
    db.add(admin)
    await db.flush()

    return BrandDetailResponse(
        id=brand.id, name=brand.name, code=brand.code,
        contact_name=brand.contact_name, contact_phone=brand.contact_phone,
        logo_url=brand.logo_url, is_active=brand.is_active,
        created_at=brand.created_at.isoformat() if brand.created_at else None,
        shop_count=1, staff_count=1,
    )


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: UUID,
    data: BrandUpdate,
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update brand info (super_admin only)."""
    if not staff.is_brand_level:
        raise HTTPException(status_code=403, detail="无权编辑品牌")

    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")
    if staff.brand_id != brand_id:
        raise HTTPException(status_code=403, detail="无权编辑该品牌")

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(brand, k, v)
    await db.flush()

    return BrandResponse(
        id=brand.id, name=brand.name, code=brand.code,
        contact_name=brand.contact_name, contact_phone=brand.contact_phone,
        logo_url=brand.logo_url, is_active=brand.is_active,
        created_at=brand.created_at.isoformat() if brand.created_at else None,
    )


@router.delete("/{brand_id}")
async def delete_brand(
    brand_id: UUID,
    staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a brand (soft delete, super_admin only)."""
    if not staff.is_brand_level:
        raise HTTPException(status_code=403, detail="无权操作品牌")

    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")
    if staff.brand_id != brand_id:
        raise HTTPException(status_code=403, detail="无权操作该品牌")

    brand.is_active = False
    await db.flush()
    return {"message": "品牌已停用"}
