"""Authentication router."""
from fastapi import APIRouter, Depends, HTTPException, status
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.staff import Staff
from app.models.shop import Shop
from app.models.brand import Brand
from app.schemas.auth import LoginRequest, TokenResponse, ChangePasswordRequest, UserResponse
from app.middleware.auth import create_access_token, get_current_staff

router = APIRouter(prefix="/api/auth", tags=["认证"])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with phone and password, returns JWT token."""
    result = await db.execute(
        select(Staff).where(Staff.phone == request.phone).options(selectinload(Staff.shop))
    )
    staff = result.scalar_one_or_none()

    if not staff or not verify_password(request.password, staff.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
        )

    if not staff.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    # Get brand info
    brand_name = ""
    if staff.brand_id:
        brand_result = await db.execute(select(Brand).where(Brand.id == staff.brand_id))
        brand = brand_result.scalar_one_or_none()
        brand_name = brand.name if brand else ""

    token = create_access_token(
        staff_id=staff.id,
        shop_id=staff.shop_id,
        role=staff.role,
        brand_id=staff.brand_id,
    )

    return TokenResponse(
        access_token=token,
        expires_in=60 * 24,  # 24 hours in minutes
        staff_id=staff.id,
        staff_name=staff.name,
        role=staff.role,
        shop_id=staff.shop_id,
        shop_name=staff.shop.name if staff.shop else "",
        brand_id=staff.brand_id,
        brand_name=brand_name,
        is_brand_level=staff.is_brand_level,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user info."""
    result = await db.execute(
        select(Staff)
        .where(Staff.id == current_staff.id)
        .options(selectinload(Staff.shop), selectinload(Staff.position))
    )
    staff = result.scalar_one()

    # Get brand info
    brand_name = ""
    if staff.brand_id:
        brand_result = await db.execute(select(Brand).where(Brand.id == staff.brand_id))
        brand = brand_result.scalar_one_or_none()
        brand_name = brand.name if brand else ""

    return UserResponse(
        id=staff.id,
        name=staff.name,
        phone=staff.phone,
        role=staff.role,
        avatar_url=staff.avatar_url,
        shop_id=staff.shop_id,
        shop_name=staff.shop.name if staff.shop else "",
        brand_id=staff.brand_id,
        brand_name=brand_name,
        is_brand_level=staff.is_brand_level,
        position_name=staff.position.name if staff.position else None,
    )


@router.put("/password")
async def change_password(
    request: ChangePasswordRequest,
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Change password for current user."""
    if not verify_password(request.old_password, current_staff.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    current_staff.password_hash = hash_password(request.new_password)
    db.add(current_staff)
    return {"message": "密码修改成功"}
