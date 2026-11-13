"""Order router - Full order lifecycle management."""
from datetime import datetime, date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.order import Order, OrderItem, Payment, PaymentMethod, OrderRecord
from app.models.customer import Customer
from app.schemas.order import (
    OrderResponse, OrderCreate,
    OrderItemResponse, PaymentResponse, OrderRecordResponse,
    OrderModifyRequest, OrderCancelRequest, OrderRefundRequest,
    OrderHoldRequest, OrderArrearsRequest, OrderSignatureRequest, OrderVerifyRequest,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api", tags=["订单管理"])


def _build_order_response(order: Order, customer_name: str | None = None) -> OrderResponse:
    """Build OrderResponse from Order model.
    
    IMPORTANT: Must be called within an async session with relationships already loaded
    via selectinload or db.refresh(). This function should NOT trigger lazy loading.
    """
    # Pre-fetch all relationship data to avoid lazy loading
    items_data = []
    payments_data = []
    records_data = []
    
    # Use getattr with default to safely access potentially unloaded relationships
    order_items = getattr(order, 'items', None) or []
    order_payments = getattr(order, 'payments', None) or []
    order_records = getattr(order, 'records', None) or []
    
    for item in order_items:
        items_data.append(OrderItemResponse(
            id=item.id,
            item_type=item.item_type,
            item_name=item.item_name,
            quantity=item.quantity,
            unit_price=float(item.unit_price) if item.unit_price is not None else 0.0,
            discount=float(item.discount) if item.discount is not None else 100.0,
            amount=float(item.amount) if item.amount is not None else 0.0,
            staff_id=item.staff_id,
        ))
    
    for p in order_payments:
        payments_data.append(PaymentResponse(
            id=p.id,
            payment_method_name=p.payment_method_name,
            amount=float(p.amount) if p.amount is not None else 0.0,
            is_refund=p.is_refund,
            created_at=p.created_at,
        ))
    
    for r in order_records:
        records_data.append(OrderRecordResponse(
            id=r.id,
            action=r.action,
            old_status=r.old_status,
            new_status=r.new_status,
            remark=r.remark,
            created_by=r.created_by,
            created_at=r.created_at,
        ))
    
    return OrderResponse(
        id=order.id,
        order_no=order.order_no,
        customer_id=order.customer_id,
        customer_name=customer_name,  # From joined query
        shop_id=order.shop_id,
        total_amount=float(order.total_amount) if order.total_amount is not None else 0.0,
        discount_amount=float(order.discount_amount) if order.discount_amount is not None else 0.0,
        paid_amount=float(order.paid_amount) if order.paid_amount is not None else 0.0,
        status=order.status,
        hold_status=order.hold_status,
        order_type=order.order_type,
        consume_type=order.consume_type,
        refund_reason=order.refund_reason,
        refund_type=order.refund_type,
        refund_amount=float(order.refund_amount) if order.refund_amount is not None else 0.0,
        refund_method=order.refund_method,
        verify_status=order.verify_status,
        verify_at=order.verify_at,
        remark=order.remark,
        items=items_data,
        payments=payments_data,
        records=records_data,
        created_by=order.created_by,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.get("/orders", response_model=PaginatedResponse[OrderResponse])
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: Optional[UUID] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    order_type: Optional[str] = None,
    verify_status: Optional[str] = None,
    has_arrears: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated order list with filters."""
    # Base query for filtering (no selectinload, no tuple select)
    base_query = (
        select(Order)
        .outerjoin(Customer, Order.customer_id == Customer.id)
        .where(Order.shop_id.in_(shop_ids))
    )

    if customer_id:
        base_query = base_query.where(Order.customer_id == customer_id)
    if status:
        base_query = base_query.where(Order.status == status)
    if search:
        base_query = base_query.where(
            or_(
                Order.order_no.ilike(f"%{search}%"),
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
            )
        )
    if order_type:
        base_query = base_query.where(Order.order_type == order_type)
    if verify_status:
        base_query = base_query.where(Order.verify_status == verify_status)
    if has_arrears == "true":
        base_query = base_query.where(Order.paid_amount < Order.total_amount)
    if start_date:
        base_query = base_query.where(Order.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        base_query = base_query.where(Order.created_at <= datetime.combine(end_date, datetime.max.time()))

    # Count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Paginated query with selectinload
    paginated_query = (
        base_query.with_only_columns(Order)
        .options(selectinload(Order.items), selectinload(Order.payments), selectinload(Order.records))
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(paginated_query)
    orders = result.scalars().all()

    # Batch fetch customer names
    customer_ids = [o.customer_id for o in orders if o.customer_id]
    customer_map: dict = {}
    if customer_ids:
        cust_result = await db.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_(customer_ids))
        )
        customer_map = {row[0]: row[1] for row in cust_result.all()}

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[_build_order_response(o, customer_name=customer_map.get(o.customer_id)) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get order detail."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items), selectinload(Order.payments), selectinload(Order.records))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # Fetch customer name
    customer_name = None
    if order.customer_id:
        cust_result = await db.execute(select(Customer.name).where(Customer.id == order.customer_id))
        customer_name = cust_result.scalar_one_or_none()
    
    return _build_order_response(order, customer_name=customer_name)


@router.post("/orders", response_model=OrderResponse)
async def create_order(
    data: OrderCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    current_staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new order (收银开单)."""
    import uuid as uuid_lib
    order_no = f"ORD{uuid_lib.uuid4().hex[:8].upper()}"

    order = Order(
        order_no=order_no,
        customer_id=data.customer_id,
        shop_id=shop_ids[0],
        order_type=data.order_type,
        consume_type=data.consume_type,
        remark=data.remark,
        created_by=current_staff.id if current_staff else None,
    )
    db.add(order)
    await db.flush()

    total_amount = 0.0
    for item_data in data.items:
        item = OrderItem(
            order_id=order.id,
            item_type=item_data.item_type,
            item_id=item_data.item_id,
            item_name=item_data.item_name,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            discount=item_data.discount,
            amount=item_data.amount,
            staff_id=item_data.staff_id,
        )
        db.add(item)
        total_amount += item_data.amount

    paid_amount = 0.0
    for payment_data in data.payments:
        payment = Payment(
            order_id=order.id,
            payment_method_id=payment_data.payment_method_id,
            payment_method_name=payment_data.payment_method_name,
            amount=payment_data.amount,
            card_id=payment_data.card_id,
        )
        db.add(payment)
        paid_amount += payment_data.amount

    order.total_amount = total_amount
    order.paid_amount = paid_amount
    if paid_amount >= total_amount:
        order.status = "paid"
    else:
        order.status = "pending"

    # 创建订单记录
    record = OrderRecord(
        order_id=order.id,
        action="create",
        new_status=order.status,
        remark=f"创建订单，应付：{total_amount}，实付：{paid_amount}",
        created_by=current_staff.id if current_staff else None,
    )
    db.add(record)

    await db.flush()
    await db.refresh(order, ["items", "payments", "records"])

    return _build_order_response(order)


@router.put("/orders/{order_id}/modify", response_model=OrderResponse)
async def modify_order(
    order_id: UUID,
    data: OrderModifyRequest,
    current_staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Modify order (改单)."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items), selectinload(Order.payments))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status not in ["pending", "paid"]:
        raise HTTPException(status_code=400, detail="当前订单状态不可改单")

    old_status = order.status

    # 删除旧品项和支付
    for item in order.items:
        await db.delete(item)
    for payment in order.payments:
        await db.delete(payment)

    # 重新添加品项
    total_amount = 0.0
    for item_data in data.items:
        item = OrderItem(
            order_id=order.id,
            item_type=item_data.item_type,
            item_id=item_data.item_id,
            item_name=item_data.item_name,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            discount=item_data.discount,
            amount=item_data.amount,
            staff_id=item_data.staff_id,
        )
        db.add(item)
        total_amount += item_data.amount

    # 重新添加支付
    paid_amount = 0.0
    for payment_data in data.payments:
        payment = Payment(
            order_id=order.id,
            payment_method_id=payment_data.payment_method_id,
            payment_method_name=payment_data.payment_method_name,
            amount=payment_data.amount,
            card_id=payment_data.card_id,
        )
        db.add(payment)
        paid_amount += payment_data.amount

    order.total_amount = total_amount
    order.paid_amount = paid_amount
    if paid_amount >= total_amount:
        order.status = "paid"
    else:
        order.status = "pending"
    order.remark = data.remark or order.remark
    order.updated_by = current_staff.id if current_staff else None

    # 记录操作
    record = OrderRecord(
        order_id=order.id,
        action="modify",
        old_status=old_status,
        new_status=order.status,
        remark=f"改单，新应付：{total_amount}，新实付：{paid_amount}",
        created_by=current_staff.id if current_staff else None,
    )
    db.add(record)

    await db.flush()
    await db.refresh(order, ["items", "payments", "records"])

    return _build_order_response(order)


@router.put("/orders/{order_id}/cancel", response_model=MessageResponse)
async def cancel_order(
    order_id: UUID,
    data: OrderCancelRequest = OrderCancelRequest(),
    current_staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Cancel order (撤销订单)."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status not in ["pending", "paid"]:
        raise HTTPException(status_code=400, detail="当前订单状态不可撤销")

    old_status = order.status
    order.status = "cancelled"
    order.updated_by = current_staff.id if current_staff else None

    record = OrderRecord(
        order_id=order.id,
        action="cancel",
        old_status=old_status,
        new_status="cancelled",
        remark=data.reason or "撤销订单",
        created_by=current_staff.id if current_staff else None,
    )
    db.add(record)
    await db.flush()

    return MessageResponse(message="订单已撤销")


@router.put("/orders/{order_id}/refund", response_model=MessageResponse)
async def refund_order(
    order_id: UUID,
    data: OrderRefundRequest,
    current_staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Refund order (退单)."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "paid":
        raise HTTPException(status_code=400, detail="只有已支付订单可退单")

    old_status = order.status
    order.status = "refunded"
    order.refund_type = data.refund_type
    order.refund_amount = data.refund_amount
    order.refund_method = data.refund_method
    order.refund_reason = data.reason
    order.updated_by = current_staff.id if current_staff else None

    record = OrderRecord(
        order_id=order.id,
        action="refund",
        old_status=old_status,
        new_status="refunded",
        remark=f"退单：{data.refund_type}，退款金额：{data.refund_amount}，原因：{data.reason}",
        created_by=current_staff.id if current_staff else None,
    )
    db.add(record)
    await db.flush()

    return MessageResponse(message="退单成功")


@router.put("/orders/{order_id}/hold", response_model=MessageResponse)
async def hold_order(
    order_id: UUID,
    data: OrderHoldRequest,
    current_staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Hold/Restore order (挂单/取回挂单)."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if data.action == "hold":
        if order.status not in ["pending", "paid"]:
            raise HTTPException(status_code=400, detail="当前订单状态不可挂单")
        order.hold_status = "hold"
        order.status = "hold"
        action_name = "挂单"
    elif data.action == "restore":
        if order.status != "hold":
            raise HTTPException(status_code=400, detail="当前订单不在挂单状态")
        order.hold_status = None
        order.status = "pending"
        action_name = "取回挂单"
    else:
        raise HTTPException(status_code=400, detail="无效的操作")

    order.updated_by = current_staff.id if current_staff else None

    record = OrderRecord(
        order_id=order.id,
        action=data.action,
        old_status=order.status,
        new_status=order.status,
        remark=data.remark or action_name,
        created_by=current_staff.id if current_staff else None,
    )
    db.add(record)
    await db.flush()

    return MessageResponse(message=f"{action_name}成功")


@router.post("/orders/{order_id}/arrears", response_model=OrderResponse)
async def pay_arrears(
    order_id: UUID,
    data: OrderArrearsRequest,
    current_staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Pay arrears (补款)."""
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.payments))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status not in ["pending", "hold"]:
        raise HTTPException(status_code=400, detail="当前订单状态不可补款")

    # 添加补款支付记录
    payment = Payment(
        order_id=order.id,
        payment_method_id=data.payment.payment_method_id,
        payment_method_name=data.payment.payment_method_name,
        amount=data.payment.amount,
        card_id=data.payment.card_id,
        is_arrears=True,
    )
    db.add(payment)

    order.paid_amount = float(order.paid_amount) + data.payment.amount
    if float(order.paid_amount) >= float(order.total_amount):
        order.status = "paid"

    order.updated_by = current_staff.id if current_staff else None

    record = OrderRecord(
        order_id=order.id,
        action="arrears",
        new_status=order.status,
        remark=f"补款：{data.payment.amount}，支付方式：{data.payment.payment_method_name}",
        created_by=current_staff.id if current_staff else None,
    )
    db.add(record)
    await db.flush()
    await db.refresh(order, ["items", "payments", "records"])

    return _build_order_response(order)


@router.put("/orders/{order_id}/signature", response_model=MessageResponse)
async def add_signature(
    order_id: UUID,
    data: OrderSignatureRequest,
    current_staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Add signature (签字)."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    order.signature_url = data.signature_url
    order.updated_by = current_staff.id if current_staff else None

    record = OrderRecord(
        order_id=order.id,
        action="signature",
        remark="添加电子签名",
        created_by=current_staff.id if current_staff else None,
    )
    db.add(record)
    await db.flush()

    return MessageResponse(message="签字成功")


@router.put("/orders/{order_id}/verify", response_model=MessageResponse)
async def verify_order(
    order_id: UUID,
    current_staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Verify order (核对/核销). No body needed - auto sets to verified."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    order.verify_status = "verified"
    order.verify_at = datetime.utcnow()
    order.updated_by = current_staff.id if current_staff else None

    record = OrderRecord(
        order_id=order.id,
        action="verify",
        remark="核对订单",
        created_by=current_staff.id if current_staff else None,
    )
    db.add(record)
    await db.flush()

    return MessageResponse(message="核销成功")


@router.get("/orders/{order_id}/records", response_model=list[OrderRecordResponse])
async def list_order_records(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get order records (轨迹)."""
    result = await db.execute(
        select(OrderRecord)
        .where(OrderRecord.order_id == order_id)
        .order_by(OrderRecord.created_at.desc())
    )
    records = result.scalars().all()
    return [
        OrderRecordResponse(
            id=r.id,
            action=r.action,
            old_status=r.old_status,
            new_status=r.new_status,
            remark=r.remark,
            created_by=r.created_by,
            created_at=r.created_at,
        )
        for r in records
    ]
