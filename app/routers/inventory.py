"""Stock order & cost accounting router - inbound/outbound records, cost summary & adjustment."""
import uuid as _uuid
from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.item import (
    Product, Inventory, InventoryLog, StockOrder, StockOrderItem,
    CostAdjustment, CostAdjustmentItem, ProductBrand, Category,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api", tags=["库存明细与成本核算"])


def _gen_order_no(prefix: str) -> str:
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}{_uuid.uuid4().hex[:4].upper()}"


# ============ 入库/出库单据 ============

@router.get("/stock-orders")
async def list_stock_orders(
    order_type: str = Query(..., description="inbound/outbound"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse: Optional[str] = None,
    stock_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    keyword: Optional[str] = None,
    supplier: Optional[str] = None,
    customer: Optional[str] = None,
    order_no: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List stock orders (inbound or outbound) with filters."""
    query = select(StockOrder).where(
        StockOrder.shop_id.in_(shop_ids),
        StockOrder.order_type == order_type,
    )
    if warehouse:
        query = query.where(StockOrder.warehouse_name == warehouse)
    if stock_type:
        query = query.where(StockOrder.stock_type == stock_type)
    if start_date:
        query = query.where(StockOrder.order_time >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.where(StockOrder.order_time <= datetime.combine(end_date, datetime.max.time()))
    if supplier:
        query = query.where(StockOrder.supplier_name.ilike(f"%{supplier}%"))
    if customer:
        query = query.where(StockOrder.customer_name.ilike(f"%{customer}%"))
    if order_no:
        query = query.where(StockOrder.order_no.ilike(f"%{order_no}%"))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    rows = (await db.execute(
        query.order_by(StockOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    items = []
    for o in rows:
        items.append({
            "id": str(o.id),
            "order_no": o.order_no,
            "order_type": o.order_type,
            "stock_type": o.stock_type,
            "warehouse_name": o.warehouse_name,
            "operator_name": o.operator_name,
            "creator_name": o.creator_name,
            "supplier_name": o.supplier_name,
            "customer_name": o.customer_name,
            "remark": o.remark,
            "order_time": o.order_time.isoformat() if o.order_time else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/stock-orders/{order_id}")
async def get_stock_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get stock order detail with items."""
    result = await db.execute(
        select(StockOrder).where(StockOrder.id == order_id).options(selectinload(StockOrder.items))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="单据不存在")

    items = []
    for it in order.items:
        items.append({
            "id": str(it.id),
            "product_id": str(it.product_id),
            "product_name": it.product_name,
            "product_code": it.product_code,
            "brand_name": it.brand_name,
            "category_name": it.category_name,
            "unit": it.unit,
            "quantity": float(it.quantity or 0),
            "cost_price": float(it.cost_price or 0),
            "cost_total": float(it.cost_total or 0),
            "production_date": it.production_date.isoformat() if it.production_date else None,
            "shelf_life_months": it.shelf_life_months,
            "expire_date": it.expire_date.isoformat() if it.expire_date else None,
            "batch_no": it.batch_no,
            "remark": it.remark,
        })

    return {
        "id": str(order.id),
        "order_no": order.order_no,
        "order_type": order.order_type,
        "stock_type": order.stock_type,
        "warehouse_name": order.warehouse_name,
        "operator_name": order.operator_name,
        "creator_name": order.creator_name,
        "remark": order.remark,
        "order_time": order.order_time.isoformat() if order.order_time else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "items": items,
    }


@router.get("/stock-order-details")
async def list_stock_order_details(
    order_type: str = Query(..., description="inbound/outbound"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse: Optional[str] = None,
    stock_type: Optional[str] = None,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    keyword: Optional[str] = None,
    sort_field: Optional[str] = None,
    sort_order: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List stock order detail items (flat list across all orders) for 入库明细/出库明细."""
    query = (
        select(StockOrderItem)
        .join(StockOrder, StockOrderItem.order_id == StockOrder.id)
        .where(
            StockOrder.shop_id.in_(shop_ids),
            StockOrder.order_type == order_type,
        )
        .options(selectinload(StockOrderItem.order))
    )
    if warehouse:
        query = query.where(StockOrder.warehouse_name == warehouse)
    if stock_type:
        query = query.where(StockOrder.stock_type == stock_type)
    if brand:
        query = query.where(StockOrderItem.brand_name.ilike(f"%{brand}%"))
    if category:
        query = query.where(StockOrderItem.category_name.ilike(f"%{category}%"))
    if start_date:
        query = query.where(StockOrder.order_time >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.where(StockOrder.order_time <= datetime.combine(end_date, datetime.max.time()))
    if keyword:
        query = query.where(or_(
            StockOrderItem.product_name.ilike(f"%{keyword}%"),
            StockOrderItem.product_code.ilike(f"%{keyword}%"),
            StockOrder.order_no.ilike(f"%{keyword}%"),
        ))

    # Sort
    if sort_field == "order_time":
        col = StockOrder.order_time
    elif sort_field == "created_at":
        col = StockOrder.created_at
    else:
        col = StockOrder.created_at
    query = query.order_by(col.desc() if sort_order != "asc" else col.asc())

    # Count & total quantity
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    total_qty = (await db.execute(
        select(func.coalesce(func.sum(StockOrderItem.quantity), 0))
        .select_from(query.subquery())
    )).scalar() or 0

    # Paged
    rows = (await db.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    # Page-level sum
    page_qty = sum(float(r.quantity or 0) for r in rows)

    items = []
    for it in rows:
        order = it.order
        items.append({
            "id": str(it.id),
            "order_no": order.order_no if order else "",
            "created_at": order.created_at.isoformat() if order and order.created_at else None,
            "order_time": order.order_time.isoformat() if order and order.order_time else None,
            "warehouse_name": order.warehouse_name if order else "",
            "stock_type": order.stock_type if order else "",
            "brand_name": it.brand_name,
            "category_name": it.category_name,
            "product_name": it.product_name,
            "product_code": it.product_code,
            "quantity": float(it.quantity or 0),
            "production_date": it.production_date.isoformat() if it.production_date else None,
            "shelf_life_months": it.shelf_life_months,
            "expire_date": it.expire_date.isoformat() if it.expire_date else None,
            "batch_no": it.batch_no,
            "creator_name": order.creator_name if order else "",
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "page_qty": round(page_qty, 2),
        "total_qty": round(float(total_qty), 2),
    }


# ============ 创建入库/出库单 ============

from pydantic import BaseModel

class StockOrderItemCreate(BaseModel):
    product_id: str
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    unit: Optional[str] = None
    quantity: float
    cost_price: float = 0
    cost_total: float = 0
    production_date: Optional[str] = None
    shelf_life_months: Optional[int] = None
    batch_no: Optional[str] = None
    remark: Optional[str] = None


class StockOrderCreate(BaseModel):
    order_type: str  # inbound / outbound
    stock_type: str  # 采购/调拨/退单/盘盈/销售/盘亏/报损等
    warehouse_name: Optional[str] = None
    operator_name: Optional[str] = None
    supplier_name: Optional[str] = None
    customer_name: Optional[str] = None
    remark: Optional[str] = None
    order_time: Optional[str] = None
    items: list[StockOrderItemCreate]


@router.post("/stock-orders")
async def create_stock_order(
    data: StockOrderCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a stock order (inbound or outbound) with items."""
    if data.order_type not in ("inbound", "outbound"):
        raise HTTPException(status_code=400, detail="无效的单据类型")
    if not data.items:
        raise HTTPException(status_code=400, detail="至少需要一个产品")

    prefix = "RK" if data.order_type == "inbound" else "CK"
    order = StockOrder(
        order_no=_gen_order_no(prefix),
        order_type=data.order_type,
        stock_type=data.stock_type,
        warehouse_name=data.warehouse_name,
        operator_name=data.operator_name,
        creator_name=data.operator_name or "system",
        supplier_name=data.supplier_name,
        customer_name=data.customer_name,
        remark=data.remark,
        shop_id=shop_ids[0],
        order_time=datetime.fromisoformat(data.order_time) if data.order_time else datetime.utcnow(),
    )

    for it in data.items:
        prod_id = UUID(it.product_id)
        # Compute expire_date
        exp_date = None
        if it.production_date and it.shelf_life_months:
            pd = date.fromisoformat(it.production_date) if isinstance(it.production_date, str) else it.production_date
            total_months = pd.month - 1 + it.shelf_life_months
            exp_date = pd.replace(year=pd.year + total_months // 12, month=total_months % 12 + 1)

        item = StockOrderItem(
            order=order,
            product_id=prod_id,
            product_name=it.product_name,
            product_code=it.product_code,
            brand_name=it.brand_name,
            category_name=it.category_name,
            unit=it.unit,
            quantity=it.quantity,
            cost_price=it.cost_price,
            cost_total=it.cost_total or (it.quantity * it.cost_price),
            production_date=date.fromisoformat(it.production_date) if it.production_date else None,
            shelf_life_months=it.shelf_life_months,
            expire_date=exp_date,
            batch_no=it.batch_no,
            remark=it.remark,
        )

        # Update inventory
        inv_result = await db.execute(
            select(Inventory).where(Inventory.product_id == prod_id, Inventory.shop_id.in_(shop_ids))
        )
        inv = inv_result.scalar_one_or_none()
        current_qty = inv.quantity if inv else 0
        current_cost = float(inv.cost_price) if inv and inv.cost_price else 0

        if data.order_type == "inbound":
            new_qty = current_qty + it.quantity
            # Weighted average cost
            if it.cost_price > 0 and current_qty + it.quantity > 0:
                new_cost = (current_cost * current_qty + it.cost_price * it.quantity) / (current_qty + it.quantity)
            else:
                new_cost = current_cost
            if inv:
                inv.quantity = new_qty
                inv.cost_price = round(new_cost, 2)
                inv.last_inbound_at = datetime.utcnow()
            else:
                inv = Inventory(
                    product_id=prod_id, shop_id=shop_ids[0],
                    quantity=int(it.quantity), cost_price=round(it.cost_price, 2),
                    last_inbound_at=datetime.utcnow(),
                )
                db.add(inv)
        else:  # outbound
            if it.quantity > current_qty:
                raise HTTPException(status_code=400, detail=f"库存不足: {it.product_name}")
            new_qty = current_qty - it.quantity
            if inv:
                inv.quantity = new_qty
                inv.last_outbound_at = datetime.utcnow()

        # Write inventory log
        log = InventoryLog(
            product_id=prod_id,
            shop_id=shop_ids[0],
            change_type=data.order_type,
            change_quantity=int(it.quantity) if data.order_type == "inbound" else -int(it.quantity),
            before_quantity=current_qty,
            after_quantity=new_qty,
            reason=f"{data.stock_type} - {order.order_no}",
        )
        db.add(log)

    db.add(order)
    await db.commit()
    await db.refresh(order)
    return {"message": f"{'入库' if data.order_type == 'inbound' else '出库'}单创建成功", "id": str(order.id)}


# ============ 成本核算 ============

@router.get("/inventory/cost/summary")
async def cost_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    warehouse: Optional[str] = None,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Cost accounting summary: opening/closing/inbound/outbound costs."""
    # Opening cost = inventory cost at start of period
    # We approximate: sum all inventory cost at start_date
    # For simplicity, compute from current inventory + historical logs

    # Inbound cost in period
    inbound_q = (
        select(func.coalesce(func.sum(StockOrderItem.cost_total), 0))
        .join(StockOrder, StockOrderItem.order_id == StockOrder.id)
        .where(
            StockOrder.shop_id.in_(shop_ids),
            StockOrder.order_type == "inbound",
            StockOrder.order_time >= datetime.combine(start_date, datetime.min.time()),
            StockOrder.order_time <= datetime.combine(end_date, datetime.max.time()),
        )
    )
    if warehouse:
        inbound_q = inbound_q.where(StockOrder.warehouse_name == warehouse)
    inbound_cost = float((await db.execute(inbound_q)).scalar() or 0)

    # Outbound cost in period
    outbound_q = (
        select(func.coalesce(func.sum(StockOrderItem.cost_total), 0))
        .join(StockOrder, StockOrderItem.order_id == StockOrder.id)
        .where(
            StockOrder.shop_id.in_(shop_ids),
            StockOrder.order_type == "outbound",
            StockOrder.order_time >= datetime.combine(start_date, datetime.min.time()),
            StockOrder.order_time <= datetime.combine(end_date, datetime.max.time()),
        )
    )
    if warehouse:
        outbound_q = outbound_q.where(StockOrder.warehouse_name == warehouse)
    outbound_cost = float((await db.execute(outbound_q)).scalar() or 0)

    # Current (closing) inventory cost
    closing_q = select(func.coalesce(func.sum(Inventory.quantity * Inventory.cost_price), 0)).where(Inventory.shop_id.in_(shop_ids))
    closing_cost = float((await db.execute(closing_q)).scalar() or 0)

    # Opening = closing - inbound + outbound
    opening_cost = closing_cost - inbound_cost + outbound_cost

    return {
        "opening_cost": round(opening_cost, 2),
        "inbound_cost": round(inbound_cost, 2),
        "outbound_cost": round(outbound_cost, 2),
        "closing_cost": round(closing_cost, 2),
    }


# ============ 成本调整 ============

class CostAdjustItemCreate(BaseModel):
    product_id: str
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    unit: Optional[str] = None
    stock_quantity: int = 0
    new_cost_price: float = 0
    remark: Optional[str] = None


class CostAdjustmentCreate(BaseModel):
    warehouse_name: Optional[str] = None
    operator_name: Optional[str] = None
    remark: Optional[str] = None
    items: list[CostAdjustItemCreate]


@router.get("/inventory/cost-adjust/products")
async def list_adjustable_products(
    warehouse: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List products available for cost adjustment."""
    query = (
        select(Inventory)
        .where(Inventory.shop_id.in_(shop_ids))
        .options(selectinload(Inventory.product).selectinload(Product.unit))
    )
    result = await db.execute(query)
    invs = result.scalars().unique().all()

    items = []
    for inv in invs:
        prod = inv.product
        items.append({
            "product_id": str(inv.product_id),
            "product_code": prod.barcode if prod else None,
            "product_name": prod.name if prod else "Unknown",
            "unit": prod.unit.name if prod and prod.unit else None,
            "stock_quantity": inv.quantity,
            "cost_price": float(inv.cost_price or 0),
            "cost_total": round(float(inv.cost_price or 0) * inv.quantity, 2),
        })
    return items


@router.post("/inventory/cost-adjust/submit", response_model=MessageResponse)
async def submit_cost_adjustment(
    data: CostAdjustmentCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Submit a cost adjustment."""
    if not data.items:
        raise HTTPException(status_code=400, detail="至少需要一个产品")

    adj = CostAdjustment(
        order_no=_gen_order_no("CB"),
        warehouse_name=data.warehouse_name,
        operator_name=data.operator_name,
        creator_name=data.operator_name or "system",
        remark=data.remark,
        shop_id=shop_ids[0],
    )

    for it in data.items:
        prod_id = UUID(it.product_id)
        # Get current inventory
        inv_result = await db.execute(
            select(Inventory).where(Inventory.product_id == prod_id, Inventory.shop_id.in_(shop_ids))
        )
        inv = inv_result.scalar_one_or_none()
        old_price = float(inv.cost_price) if inv and inv.cost_price else 0

        item = CostAdjustmentItem(
            adjustment=adj,
            product_id=prod_id,
            product_name=it.product_name,
            product_code=it.product_code,
            unit=it.unit,
            stock_quantity=it.stock_quantity,
            old_cost_price=old_price,
            new_cost_price=it.new_cost_price,
            cost_total=round(it.new_cost_price * it.stock_quantity, 2),
            remark=it.remark,
        )

        # Update inventory cost price
        if inv:
            inv.cost_price = it.new_cost_price

    db.add(adj)
    await db.commit()
    return MessageResponse(message="成本调整提交成功")


@router.get("/inventory/cost-adjust/records")
async def list_cost_adjustments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    keyword: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List cost adjustment records."""
    query = select(CostAdjustment).where(CostAdjustment.shop_id.in_(shop_ids))
    if warehouse:
        query = query.where(CostAdjustment.warehouse_name == warehouse)
    if start_date:
        query = query.where(CostAdjustment.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.where(CostAdjustment.created_at <= datetime.combine(end_date, datetime.max.time()))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    rows = (await db.execute(
        query.order_by(CostAdjustment.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    items = []
    for r in rows:
        items.append({
            "id": str(r.id),
            "order_no": r.order_no,
            "warehouse_name": r.warehouse_name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "creator_name": r.creator_name,
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/inventory/cost-adjust/records/{record_id}")
async def get_cost_adjustment(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get cost adjustment detail with items."""
    result = await db.execute(
        select(CostAdjustment).where(CostAdjustment.id == record_id).options(selectinload(CostAdjustment.items))
    )
    adj = result.scalar_one_or_none()
    if not adj:
        raise HTTPException(status_code=404, detail="调整记录不存在")

    items = []
    for it in adj.items:
        items.append({
            "product_id": str(it.product_id),
            "product_name": it.product_name,
            "product_code": it.product_code,
            "unit": it.unit,
            "stock_quantity": it.stock_quantity,
            "old_cost_price": float(it.old_cost_price or 0),
            "new_cost_price": float(it.new_cost_price or 0),
            "cost_total": float(it.cost_total or 0),
            "remark": it.remark,
        })

    return {
        "id": str(adj.id),
        "order_no": adj.order_no,
        "warehouse_name": adj.warehouse_name,
        "operator_name": adj.operator_name,
        "creator_name": adj.creator_name,
        "remark": adj.remark,
        "created_at": adj.created_at.isoformat() if adj.created_at else None,
        "items": items,
    }
