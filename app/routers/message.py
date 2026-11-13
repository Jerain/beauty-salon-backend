"""Message router - notifications and settings."""
from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.message import Message, MessageSetting
from app.models.card import MemberCard
from app.models.customer import Customer
from app.models.appointment import Appointment
from app.schemas.message import (
    MessageResponse, MessageCreate,
    MessageOverviewResponse, MessageCountResponse,
    MessageSettingResponse, MessageSettingUpdate,
)
from app.schemas.common import MessageResponse as MsgResp
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api", tags=["消息通知"])


# ============ Messages ============

@router.get("/messages", response_model=list[MessageResponse])
async def list_messages(
    message_type: Optional[str] = None,
    is_read: Optional[bool] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    query = select(Message).where(Message.shop_id.in_(shop_ids))
    if message_type:
        query = query.where(Message.message_type == message_type)
    if is_read is not None:
        query = query.where(Message.is_read == is_read)
    query = query.order_by(Message.created_at.desc()).limit(100)
    result = await db.execute(query)
    return [MessageResponse.model_validate(m) for m in result.scalars().all()]


@router.post("/messages", response_model=MessageResponse)
async def create_message(
    data: MessageCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    msg = Message(
        shop_id=shop_ids[0], staff_id=data.staff_id,
        title=data.title, content=data.content,
        message_type=data.message_type,
        related_id=data.related_id, related_type=data.related_type,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return MessageResponse.model_validate(msg)


@router.put("/messages/{message_id}/read", response_model=MsgResp)
async def mark_message_read(message_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    msg.is_read = True
    db.add(msg)
    return MsgResp(message="已标记为已读")


@router.put("/messages/read-all", response_model=MsgResp)
async def mark_all_read(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message).where(and_(Message.shop_id.in_(shop_ids), Message.is_read == False))
    )
    msgs = result.scalars().all()
    for m in msgs:
        m.is_read = True
        db.add(m)
    return MsgResp(message=f"已标记{len(msgs)}条消息为已读")


@router.delete("/messages/{message_id}", response_model=MsgResp)
async def delete_message(message_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    await db.delete(msg)
    return MsgResp(message="删除成功")


# ============ Message Overview & Count ============

@router.get("/messages/overview", response_model=MessageOverviewResponse)
async def message_overview(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    base = select(Message).where(Message.shop_id.in_(shop_ids))
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    unread = (await db.execute(
        select(func.count()).select_from(base.where(Message.is_read == False).subquery())
    )).scalar() or 0

    type_counts = {}
    for mtype in ["card_expire", "recharge", "birthday", "no_visit", "appointment", "system"]:
        cnt = (await db.execute(
            select(func.count()).select_from(
                base.where(Message.message_type == mtype).subquery()
            )
        )).scalar() or 0
        type_counts[mtype] = cnt

    return MessageOverviewResponse(
        total=total, unread=unread,
        card_expire=type_counts.get("card_expire", 0),
        recharge=type_counts.get("recharge", 0),
        birthday=type_counts.get("birthday", 0),
        no_visit=type_counts.get("no_visit", 0),
        appointment=type_counts.get("appointment", 0),
        system=type_counts.get("system", 0),
    )


@router.get("/messages/count", response_model=MessageCountResponse)
async def message_count(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    unread = (await db.execute(
        select(func.count()).where(
            and_(Message.shop_id.in_(shop_ids), Message.is_read == False)
        )
    )).scalar() or 0
    return MessageCountResponse(unread_count=unread)


# ============ Reminder Endpoints ============

@router.get("/messages/card-expire", response_model=list)
async def card_expire_reminders(
    days: int = Query(7, description="Days before expiration"),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get cards expiring within N days."""
    today = date.today()
    deadline = today + timedelta(days=days)
    result = await db.execute(
        select(MemberCard)
        .join(Customer, MemberCard.customer_id == Customer.id)
        .where(and_(
            Customer.shop_id.in_(shop_ids),
            MemberCard.status == "active",
            MemberCard.expire_date <= deadline,
            MemberCard.expire_date >= today,
        ))
    )
    cards = result.scalars().all()
    return [
        {
            "card_id": str(c.id),
            "customer_id": str(c.customer_id),
            "expire_date": c.expire_date.isoformat() if c.expire_date else None,
            "remaining_days": (c.expire_date - today).days if c.expire_date else None,
        }
        for c in cards
    ]


@router.get("/messages/customer-birthday", response_model=list)
async def birthday_reminders(
    days: int = Query(3, description="Days before birthday"),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get customers with upcoming birthdays."""
    today = date.today()
    result = await db.execute(
        select(Customer).where(
            and_(Customer.shop_id.in_(shop_ids), Customer.birthday.isnot(None))
        )
    )
    customers = result.scalars().all()
    upcoming = []
    for c in customers:
        if c.birthday:
            bday_this_year = c.birthday.replace(year=today.year)
            if bday_this_year < today:
                bday_this_year = bday_this_year.replace(year=today.year + 1)
            days_until = (bday_this_year - today).days
            if 0 <= days_until <= days:
                upcoming.append({
                    "customer_id": str(c.id),
                    "name": c.name,
                    "birthday": c.birthday.isoformat(),
                    "days_until": days_until,
                })
    return upcoming


@router.get("/messages/customer-not-to-shop", response_model=list)
async def no_visit_reminders(
    days: int = Query(30, description="Days since last visit"),
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get customers who haven't visited in N days."""
    from app.models.order import Order
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(Customer).where(Customer.shop_id.in_(shop_ids))
    )
    customers = result.scalars().all()
    alerts = []
    for c in customers:
        last_order = await db.execute(
            select(func.max(Order.created_at)).where(Order.customer_id == c.id)
        )
        last_visit = last_order.scalar()
        if last_visit is None or last_visit < cutoff:
            days_ago = (datetime.utcnow() - last_visit).days if last_visit else None
            alerts.append({
                "customer_id": str(c.id),
                "name": c.name,
                "last_visit": last_visit.isoformat() if last_visit else None,
                "days_since": days_ago,
            })
    return alerts[:50]  # limit


# ============ Message Settings ============

@router.get("/message-settings", response_model=MessageSettingResponse | None)
async def get_message_settings(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MessageSetting).where(MessageSetting.shop_id.in_(shop_ids))
    )
    setting = result.scalar_one_or_none()
    return MessageSettingResponse.model_validate(setting) if setting else None


@router.post("/message-settings", response_model=MessageSettingResponse)
async def create_or_update_message_settings(
    data: MessageSettingUpdate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MessageSetting).where(MessageSetting.shop_id.in_(shop_ids))
    )
    setting = result.scalar_one_or_none()
    if setting:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(setting, field, value)
    else:
        setting = MessageSetting(shop_id=shop_ids[0], **data.model_dump(exclude_unset=True))
    db.add(setting)
    await db.flush()
    await db.refresh(setting)
    return MessageSettingResponse.model_validate(setting)
