"""Application settings router - generic config CRUD."""
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.app_setting import AppSetting
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api/app-settings", tags=["应用设置"])


class AppSettingCreate(BaseModel):
    setting_type: str
    name: str
    data: dict | None = None
    sort_order: int = 0


class AppSettingUpdate(BaseModel):
    name: str | None = None
    data: dict | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class AppSettingResponse(BaseModel):
    id: UUID
    shop_id: UUID
    setting_type: str
    name: str
    data: dict | None = None
    is_active: bool
    sort_order: int
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AppSettingResponse])
async def list_settings(
    setting_type: str,
    is_active: Optional[bool] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List settings by type."""
    query = select(AppSetting).where(
        AppSetting.shop_id.in_(shop_ids),
        AppSetting.setting_type == setting_type,
    )
    if is_active is not None:
        query = query.where(AppSetting.is_active == is_active)
    query = query.order_by(AppSetting.sort_order.asc(), AppSetting.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        AppSettingResponse(
            id=s.id, shop_id=s.shop_id, setting_type=s.setting_type,
            name=s.name, data=s.data, is_active=s.is_active,
            sort_order=s.sort_order,
            created_at=s.created_at.isoformat() if s.created_at else None,
            updated_at=s.updated_at.isoformat() if s.updated_at else None,
        )
        for s in items
    ]


@router.post("", response_model=AppSettingResponse)
async def create_setting(
    body: AppSettingCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a setting entry."""
    item = AppSetting(
        shop_id=shop_ids[0],
        setting_type=body.setting_type,
        name=body.name,
        data=body.data or {},
        sort_order=body.sort_order,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return AppSettingResponse(
        id=item.id, shop_id=item.shop_id, setting_type=item.setting_type,
        name=item.name, data=item.data, is_active=item.is_active,
        sort_order=item.sort_order,
        created_at=item.created_at.isoformat() if item.created_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )


@router.put("/{setting_id}", response_model=AppSettingResponse)
async def update_setting(
    setting_id: UUID,
    body: AppSettingUpdate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Update a setting entry."""
    result = await db.execute(
        select(AppSetting).where(AppSetting.id == setting_id, AppSetting.shop_id.in_(shop_ids))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="设置项不存在")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(item, k, v)
    await db.commit()
    await db.refresh(item)
    return AppSettingResponse(
        id=item.id, shop_id=item.shop_id, setting_type=item.setting_type,
        name=item.name, data=item.data, is_active=item.is_active,
        sort_order=item.sort_order,
        created_at=item.created_at.isoformat() if item.created_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )


@router.delete("/{setting_id}")
async def delete_setting(
    setting_id: UUID,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Delete a setting entry."""
    result = await db.execute(
        select(AppSetting).where(AppSetting.id == setting_id, AppSetting.shop_id.in_(shop_ids))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="设置项不存在")
    await db.delete(item)
    await db.commit()
    return {"message": "已删除"}
