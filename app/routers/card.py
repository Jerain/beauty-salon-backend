"""Card router - Full card lifecycle management."""
import uuid
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.card import CardType, MemberCard, CardTransaction
from app.schemas.card import (
    CardTypeResponse, CardTypeCreate, CardTypeUpdate,
    MemberCardResponse, MemberCardCreate, MemberCardRecharge,
    MemberCardBalanceAdjust, MemberCardFreeze, MemberCardDelay,
    MemberCardTransfer, MemberCardRemark, MemberCardRefund, MemberCardConsume,
    CardTransactionResponse,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api", tags=["会员卡"])


# ============ Helper ============

def _card_response(c: MemberCard) -> MemberCardResponse:
    """Build MemberCard response without lazy loading."""
    cust = getattr(c, "customer", None)
    ct = getattr(c, "card_type", None)
    return MemberCardResponse(
        id=c.id, customer_id=c.customer_id,
        customer_name=cust.name if cust else None,
        card_type_id=c.card_type_id,
        card_type_name=ct.name if ct else None,
        card_category=ct.card_category if ct else None,
        card_no=c.card_no,
        principal_balance=float(c.principal_balance),
        present_balance=float(c.present_balance),
        total_times=c.total_times, remaining_times=c.remaining_times,
        status=c.status, activate_date=c.activate_date,
        expire_date=c.expire_date, remark=c.remark,
        shop_id=c.shop_id, created_at=c.created_at,
    )


async def _load_card(db: AsyncSession, card_id: UUID) -> MemberCard:
    """Load card with eager relationships."""
    result = await db.execute(
        select(MemberCard).where(MemberCard.id == card_id)
        .options(selectinload(MemberCard.customer), selectinload(MemberCard.card_type))
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="会员卡不存在")
    return card


def _gen_card_no() -> str:
    """Generate a unique card number."""
    return f"MC{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"


async def _write_transaction(
    db: AsyncSession, card: MemberCard, tx_type: str,
    principal_change: float = 0.0, present_change: float = 0.0,
    times_change: int = 0, order_id: UUID = None,
    operator_id: UUID = None, remark: str = None,
):
    """Write a card transaction record."""
    tx = CardTransaction(
        member_card_id=card.id, customer_id=card.customer_id,
        order_id=order_id, transaction_type=tx_type,
        principal_change=principal_change, present_change=present_change,
        times_change=times_change if times_change else None,
        before_principal=float(card.principal_balance) - principal_change,
        after_principal=float(card.principal_balance),
        before_present=float(card.present_balance) - present_change,
        after_present=float(card.present_balance),
        before_times=(card.remaining_times or 0) - times_change if card.total_times else None,
        after_times=card.remaining_times if card.total_times else None,
        operator_id=operator_id, remark=remark,
    )
    db.add(tx)


# ============ Card Types CRUD ============

@router.get("/card-types", response_model=list[CardTypeResponse])
async def list_card_types(
    include_inactive: bool = False,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List all card types."""
    query = select(CardType).where(CardType.shop_id.in_(shop_ids))
    if not include_inactive:
        query = query.where(CardType.is_active == True)
    result = await db.execute(query.order_by(CardType.created_at.desc()))
    types = result.scalars().all()
    return [CardTypeResponse.model_validate(t) for t in types]


@router.post("/card-types", response_model=CardTypeResponse)
async def create_card_type(
    data: CardTypeCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a new card type."""
    card_type = CardType(
        name=data.name, card_category=data.card_category,
        sell_price=data.sell_price, face_value=data.face_value,
        present_amount=data.present_amount, present_items=data.present_items,
        validity_type=data.validity_type, validity_days=data.validity_days,
        start_date=data.start_date, end_date=data.end_date,
        consume_rule=data.consume_rule, applicable_shops=data.applicable_shops,
        description=data.description, shop_id=shop_ids[0],
    )
    db.add(card_type)
    await db.flush()
    await db.refresh(card_type)
    return CardTypeResponse.model_validate(card_type)


@router.put("/card-types/{type_id}", response_model=CardTypeResponse)
async def update_card_type(
    type_id: UUID,
    data: CardTypeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a card type."""
    result = await db.execute(select(CardType).where(CardType.id == type_id))
    ct = result.scalar_one_or_none()
    if not ct:
        raise HTTPException(status_code=404, detail="卡类型不存在")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ct, field, value)
    db.add(ct)
    return CardTypeResponse.model_validate(ct)


@router.put("/card-types/{type_id}/status", response_model=MessageResponse)
async def toggle_card_type_status(
    type_id: UUID,
    is_active: bool = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a card type."""
    result = await db.execute(select(CardType).where(CardType.id == type_id))
    ct = result.scalar_one_or_none()
    if not ct:
        raise HTTPException(status_code=404, detail="卡类型不存在")
    ct.is_active = is_active
    db.add(ct)
    return MessageResponse(message=f"{'启用' if is_active else '停用'}成功")


@router.delete("/card-types/{type_id}", response_model=MessageResponse)
async def delete_card_type(
    type_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a card type (only if no cards issued)."""
    result = await db.execute(select(CardType).where(CardType.id == type_id))
    ct = result.scalar_one_or_none()
    if not ct:
        raise HTTPException(status_code=404, detail="卡类型不存在")
    # Check if any member cards use this type
    count = (await db.execute(
        select(func.count()).select_from(MemberCard).where(MemberCard.card_type_id == type_id)
    )).scalar()
    if count > 0:
        raise HTTPException(status_code=400, detail=f"已有{count}张会员卡使用此类型，不可删除")
    await db.delete(ct)
    return MessageResponse(message="删除成功")


# ============ Member Cards ============

@router.get("/member-cards", response_model=PaginatedResponse[MemberCardResponse])
async def list_member_cards(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: Optional[UUID] = None,
    status: Optional[str] = None,
    card_category: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated member card list."""
    query = (
        select(MemberCard)
        .where(MemberCard.shop_id.in_(shop_ids))
        .options(selectinload(MemberCard.customer), selectinload(MemberCard.card_type))
    )
    if customer_id:
        query = query.where(MemberCard.customer_id == customer_id)
    if status:
        query = query.where(MemberCard.status == status)
    if card_category:
        query = query.join(CardType).where(CardType.card_category == card_category)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = query.order_by(MemberCard.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    cards = result.scalars().unique().all()
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[_card_response(c) for c in cards],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("/member-cards", response_model=MemberCardResponse)
async def create_member_card(
    data: MemberCardCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create (activate) a new member card."""
    # Validate card type
    ct_result = await db.execute(
        select(CardType).where(CardType.id == data.card_type_id)
    )
    ct = ct_result.scalar_one_or_none()
    if not ct:
        raise HTTPException(status_code=404, detail="卡类型不存在")
    if not ct.is_active:
        raise HTTPException(status_code=400, detail="该卡类型已停用")

    card_no = data.card_no or _gen_card_no()

    # Set up initial balances
    principal = data.principal_amount if data.principal_amount > 0 else float(ct.face_value)
    present = data.present_amount if data.present_amount > 0 else float(ct.present_amount or 0)

    card = MemberCard(
        customer_id=data.customer_id, card_type_id=data.card_type_id,
        card_no=card_no,
        principal_balance=principal, present_balance=present,
        total_times=data.total_times, remaining_times=data.total_times,
        status="active", shop_id=shop_ids[0],
        activate_date=datetime.utcnow(),
        expire_date=data.expire_date,
        remark=data.remark,
    )

    # Auto-calculate expire date from card type validity
    if not data.expire_date:
        if ct.validity_type == "days" and ct.validity_days:
            card.expire_date = datetime.utcnow() + timedelta(days=ct.validity_days)
        elif ct.validity_type == "fixed" and ct.end_date:
            card.expire_date = datetime.combine(ct.end_date, datetime.max.time())

    # For times card, set total_times from face_value if not provided
    if ct.card_category == "times" and not data.total_times:
        card.total_times = int(ct.face_value)
        card.remaining_times = int(ct.face_value)

    db.add(card)
    await db.flush()

    # Write activation transaction
    await _write_transaction(
        db, card, "activate",
        principal_change=principal, present_change=present,
        times_change=card.total_times or 0,
        remark=f"开卡激活: {ct.name}",
    )

    # Re-query with eager loading
    card = await _load_card(db, card.id)
    return _card_response(card)


@router.get("/member-cards/{card_id}", response_model=MemberCardResponse)
async def get_member_card(
    card_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get member card detail."""
    card = await _load_card(db, card_id)
    return _card_response(card)


# ============ Card Operations ============

@router.post("/member-cards/{card_id}/recharge", response_model=MemberCardResponse)
async def recharge_member_card(
    card_id: UUID,
    data: MemberCardRecharge,
    db: AsyncSession = Depends(get_db),
):
    """Recharge a stored-value card."""
    card = await _load_card(db, card_id)
    if card.status != "active":
        raise HTTPException(status_code=400, detail="只有正常状态的卡可以充值")

    card.principal_balance = float(card.principal_balance) + data.amount
    card.present_balance = float(card.present_balance) + data.present_amount
    db.add(card)

    await _write_transaction(
        db, card, "recharge",
        principal_change=data.amount, present_change=data.present_amount,
        remark=data.remark or f"充值(支付方式:{data.payment_method})",
    )

    card = await _load_card(db, card.id)
    return _card_response(card)


@router.post("/member-cards/{card_id}/adjust", response_model=MemberCardResponse)
async def adjust_member_card_balance(
    card_id: UUID,
    data: MemberCardBalanceAdjust,
    db: AsyncSession = Depends(get_db),
):
    """Manually adjust card balance."""
    card = await _load_card(db, card_id)

    new_principal = float(card.principal_balance) + data.principal_change
    new_present = float(card.present_balance) + data.present_change
    new_times = (card.remaining_times or 0) + data.times_change if card.total_times else None

    if new_principal < 0 or new_present < 0:
        raise HTTPException(status_code=400, detail="调整后余额不能为负")
    if new_times is not None and new_times < 0:
        raise HTTPException(status_code=400, detail="调整后次数不能为负")

    card.principal_balance = new_principal
    card.present_balance = new_present
    if new_times is not None:
        card.remaining_times = new_times
    db.add(card)

    await _write_transaction(
        db, card, "adjust",
        principal_change=data.principal_change,
        present_change=data.present_change,
        times_change=data.times_change,
        remark=data.remark or "手动余额调整",
    )

    card = await _load_card(db, card.id)
    return _card_response(card)


@router.post("/member-cards/{card_id}/freeze", response_model=MemberCardResponse)
async def freeze_member_card(
    card_id: UUID,
    data: MemberCardFreeze,
    db: AsyncSession = Depends(get_db),
):
    """Freeze or unfreeze a member card."""
    card = await _load_card(db, card_id)

    if data.action == "freeze":
        if card.status != "active":
            raise HTTPException(status_code=400, detail="只有正常状态的卡可以冻结")
        card.status = "frozen"
    elif data.action == "unfreeze":
        if card.status != "frozen":
            raise HTTPException(status_code=400, detail="只有冻结状态的卡可以解冻")
        card.status = "active"
    else:
        raise HTTPException(status_code=400, detail="action 必须为 freeze 或 unfreeze")

    card.remark = data.remark
    db.add(card)
    card = await _load_card(db, card.id)
    return _card_response(card)


@router.post("/member-cards/{card_id}/delay", response_model=MemberCardResponse)
async def delay_member_card(
    card_id: UUID,
    data: MemberCardDelay,
    db: AsyncSession = Depends(get_db),
):
    """Extend card expiry date."""
    card = await _load_card(db, card_id)
    if card.status in ("refunded", "used_up"):
        raise HTTPException(status_code=400, detail="已退或已用完的卡不可延期")

    if card.expire_date:
        card.expire_date = card.expire_date + timedelta(days=data.days)
    else:
        card.expire_date = datetime.utcnow() + timedelta(days=data.days)

    if data.remark:
        card.remark = data.remark
    db.add(card)
    card = await _load_card(db, card.id)
    return _card_response(card)


@router.post("/member-cards/{card_id}/transfer", response_model=MessageResponse)
async def transfer_member_card(
    card_id: UUID,
    data: MemberCardTransfer,
    db: AsyncSession = Depends(get_db),
):
    """Transfer card to another customer."""
    card = await _load_card(db, card_id)
    if card.status != "active":
        raise HTTPException(status_code=400, detail="只有正常状态的卡可以转赠")
    if card.customer_id == data.target_customer_id:
        raise HTTPException(status_code=400, detail="不能转赠给自己")

    old_customer_id = card.customer_id
    card.customer_id = data.target_customer_id
    card.remark = data.remark or f"从顾客{old_customer_id}转赠"
    db.add(card)

    await _write_transaction(
        db, card, "transfer",
        remark=f"转赠给顾客 {data.target_customer_id}",
    )

    return MessageResponse(message="转赠成功")


@router.put("/member-cards/{card_id}/remark", response_model=MessageResponse)
async def update_member_card_remark(
    card_id: UUID,
    data: MemberCardRemark,
    db: AsyncSession = Depends(get_db),
):
    """Update card remark."""
    card = await _load_card(db, card_id)
    card.remark = data.remark
    db.add(card)
    return MessageResponse(message="备注更新成功")


@router.post("/member-cards/{card_id}/refund", response_model=MemberCardResponse)
async def refund_member_card(
    card_id: UUID,
    data: MemberCardRefund,
    db: AsyncSession = Depends(get_db),
):
    """Refund (return) a member card."""
    card = await _load_card(db, card_id)
    if card.status in ("refunded", "used_up"):
        raise HTTPException(status_code=400, detail="已退或已用完的卡不可退卡")

    # Check for pending orders (basic check)
    remaining = float(card.principal_balance) + float(card.present_balance)

    card.status = "refunded"
    card.remark = data.reason or "退卡"
    db.add(card)

    await _write_transaction(
        db, card, "refund",
        principal_change=-float(card.principal_balance),
        present_change=-float(card.present_balance),
        remark=f"退卡: {data.reason or '无原因'}",
    )

    # Zero out balance after transaction record
    card.principal_balance = 0
    card.present_balance = 0
    if card.total_times:
        card.remaining_times = 0
    db.add(card)

    card = await _load_card(db, card.id)
    return _card_response(card)


@router.post("/member-cards/{card_id}/consume", response_model=MemberCardResponse)
async def consume_member_card(
    card_id: UUID,
    data: MemberCardConsume,
    db: AsyncSession = Depends(get_db),
):
    """Consume from card (called by POS/checkout)."""
    card = await _load_card(db, card_id)
    if card.status != "active":
        raise HTTPException(status_code=400, detail="只有正常状态的卡可以消费")

    # Handle amount consumption
    principal_deduct = 0.0
    present_deduct = 0.0
    if data.amount > 0:
        total_balance = float(card.principal_balance) + float(card.present_balance)
        if total_balance < data.amount:
            raise HTTPException(status_code=400, detail=f"余额不足(当前{total_balance}元)")

        # Deduct from principal first, then present
        principal_available = float(card.principal_balance)
        if principal_available >= data.amount:
            principal_deduct = data.amount
            present_deduct = 0.0
        else:
            principal_deduct = principal_available
            present_deduct = data.amount - principal_available

        card.principal_balance = float(card.principal_balance) - principal_deduct
        card.present_balance = float(card.present_balance) - present_deduct

    # Handle times consumption
    times_deduct = 0
    if data.times > 0 and card.total_times:
        if (card.remaining_times or 0) < data.times:
            raise HTTPException(status_code=400, detail=f"次数不足(剩余{card.remaining_times}次)")
        card.remaining_times = (card.remaining_times or 0) - data.times
        times_deduct = data.times

        # Auto mark as used_up
        if card.remaining_times <= 0 and float(card.principal_balance) + float(card.present_balance) <= 0:
            card.status = "used_up"

    db.add(card)

    await _write_transaction(
        db, card, "consume",
        principal_change=-principal_deduct, present_change=-present_deduct,
        times_change=-times_deduct, order_id=data.order_id,
        remark=data.remark or "卡消费",
    )

    card = await _load_card(db, card.id)
    return _card_response(card)


# ============ Card Transactions ============

@router.get("/member-cards/{card_id}/transactions", response_model=PaginatedResponse[CardTransactionResponse])
async def list_card_transactions(
    card_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    transaction_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get transaction history for a card."""
    query = select(CardTransaction).where(CardTransaction.member_card_id == card_id)
    if transaction_type:
        query = query.where(CardTransaction.transaction_type == transaction_type)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = query.order_by(CardTransaction.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    txs = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[CardTransactionResponse.model_validate(t) for t in txs],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.get("/customer/{customer_id}/card-transactions", response_model=PaginatedResponse[CardTransactionResponse])
async def list_customer_card_transactions(
    customer_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get all card transactions for a customer."""
    query = select(CardTransaction).where(CardTransaction.customer_id == customer_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = query.order_by(CardTransaction.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    txs = result.scalars().all()
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[CardTransactionResponse.model_validate(t) for t in txs],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )
