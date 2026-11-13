"""JWT Authentication middleware and dependencies."""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.staff import Staff
from app.models.shop import Shop

security = HTTPBearer()


def create_access_token(staff_id: UUID, shop_id: UUID, role: str, brand_id: UUID | None = None) -> str:
    """Create a JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": str(staff_id),
        "shop_id": str(shop_id),
        "role": role,
        "exp": expire,
    }
    if brand_id:
        payload["brand_id"] = str(brand_id)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_staff(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    """Get the current authenticated staff member."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        staff_id: str = payload.get("sub")
        if staff_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(Staff).where(Staff.id == UUID(staff_id)))
    staff = result.scalar_one_or_none()

    if staff is None or not staff.is_active:
        raise credentials_exception

    return staff


async def get_current_shop_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    """Get the shop ID from the JWT token (backward compatible)."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        shop_id: str = payload.get("shop_id")
        if shop_id is None:
            raise HTTPException(status_code=401, detail="Invalid token: missing shop_id")
        return UUID(shop_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_effective_shop_ids(
    staff: Staff = Depends(get_current_staff),
    x_shop_id: Optional[str] = Header(None, alias="X-Shop-Id"),
    db: AsyncSession = Depends(get_db),
) -> list[UUID]:
    """Return the list of shop IDs the current user can access.

    - super_admin / brand_manager:
        - X-Shop-Id provided → return that single shop (verified brand membership)
        - No X-Shop-Id → return ALL shops under the brand
    - Other roles:
        - Always return [staff.shop_id] regardless of header
    """
    # Non-brand-level roles: always return own shop
    if not staff.is_brand_level:
        return [staff.shop_id]

    # Brand-level roles
    if x_shop_id:
        # Verify the selected shop belongs to the same brand
        try:
            selected_id = UUID(x_shop_id)
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid X-Shop-Id format")

        result = await db.execute(select(Shop).where(Shop.id == selected_id))
        shop = result.scalar_one_or_none()
        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")
        if staff.brand_id and shop.brand_id != staff.brand_id:
            raise HTTPException(status_code=403, detail="No access to this shop")
        return [selected_id]
    else:
        # No specific shop selected → all shops under the brand
        if not staff.brand_id:
            return [staff.shop_id]
        result = await db.execute(
            select(Shop.id).where(Shop.brand_id == staff.brand_id, Shop.is_active == True)
        )
        shop_ids = [row[0] for row in result.all()]
        if not shop_ids:
            return [staff.shop_id]
        return shop_ids
