"""Item router - Categories, ServiceProjects, Products, Inventory, Brands, Units, Tickets."""
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.item import (
    Category, ServiceProject, Product, Inventory, InventoryLog,
    ProductBrand, ProductUnit, ProjectProduct, Ticket, PriceTemplate,
)
from app.schemas.item import (
    CategoryResponse, CategoryCreate, CategoryUpdate, CategoryTreeResponse,
    ServiceProjectResponse, ServiceProjectCreate, ServiceProjectUpdate,
    ProjectStatusUpdate, ProjectProductItem,
    ProductResponse, ProductCreate, ProductUpdate,
    BrandResponse, BrandCreate,
    ProductUnitResponse, ProductUnitCreate,
    InventoryResponse, InventoryLogResponse, InventoryOperation,
    InventoryBatchOperation, StockAlertItem,
    TicketResponse, TicketCreate, TicketUpdate,
    PriceTemplateResponse, PriceTemplateCreate, PriceTemplateBatchCreate,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.middleware.auth import get_effective_shop_ids, get_current_staff

router = APIRouter(prefix="/api", tags=["品项管理"])


# ============ Helper ============

def _build_project_response(p: ServiceProject) -> ServiceProjectResponse:
    """Build project response without lazy loading."""
    linked = []
    raw_linked = getattr(p, "linked_products", None)
    if raw_linked:
        for lp in raw_linked:
            prod = getattr(lp, "product", None)
            linked.append(ProjectProductItem(
                product_id=lp.product_id,
                product_name=prod.name if prod else None,
                quantity=lp.quantity,
            ))
    cat = getattr(p, "category", None)
    return ServiceProjectResponse(
        id=p.id, name=p.name, category_id=p.category_id,
        category_name=cat.name if cat else None,
        image_url=p.image_url, price=float(p.price),
        member_price=float(p.member_price) if p.member_price else None,
        duration=p.duration, description=p.description,
        commission_rate=float(p.commission_rate) if p.commission_rate else None,
        commission_amount=float(p.commission_amount) if p.commission_amount else None,
        shop_id=p.shop_id, is_active=p.is_active, created_at=p.created_at,
        linked_products=linked,
    )


def _build_product_response(p: Product) -> ProductResponse:
    cat = getattr(p, "category", None)
    return ProductResponse(
        id=p.id, name=p.name, brand_id=p.brand_id,
        brand_name=p.brand_name,
        category_id=p.category_id,
        category_name=cat.name if cat else None,
        image_url=p.image_url, sell_price=float(p.sell_price),
        cost_price=float(p.cost_price) if p.cost_price else None,
        spec=p.spec, unit_id=p.unit_id, unit_name=p.unit_name,
        barcode=p.barcode, stock_quantity=p.stock_quantity,
        stock_alert_value=p.stock_alert_value,
        shelf_life_days=p.shelf_life_days,
        expire_date=p.expire_date, deduct_stock=p.deduct_stock,
        description=p.description, shop_id=p.shop_id,
        is_active=p.is_active, created_at=p.created_at,
    )


# ============ Categories ============

@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    category_type: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List all categories (flat)."""
    query = select(Category).where(Category.shop_id.in_(shop_ids), Category.is_active == True)
    if category_type:
        query = query.where(Category.category_type == category_type)
    result = await db.execute(query.order_by(Category.sort_order))
    categories = result.scalars().all()
    return [CategoryResponse.model_validate(c) for c in categories]


@router.get("/categories/tree", response_model=list[CategoryTreeResponse])
async def get_category_tree(
    category_type: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get category tree structure."""
    query = select(Category).where(Category.shop_id.in_(shop_ids), Category.is_active == True)
    if category_type:
        query = query.where(Category.category_type == category_type)
    result = await db.execute(query.order_by(Category.sort_order))
    all_cats = result.scalars().all()

    # Build tree in memory to avoid lazy loading issues
    cat_map: dict[UUID, list] = {}
    roots = []

    for cat in all_cats:
        cat_map.setdefault(cat.id, [])  # ensure key exists

    for cat in all_cats:
        node = CategoryTreeResponse(
            id=cat.id, name=cat.name, category_type=cat.category_type,
            sort_order=cat.sort_order, children=cat_map.get(cat.id, []),
        )
        if cat.parent_id and cat.parent_id in cat_map:
            cat_map[cat.parent_id].append(node)
        elif not cat.parent_id:
            roots.append(node)

    return roots


@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    data: CategoryCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a new category."""
    category = Category(
        name=data.name, category_type=data.category_type,
        parent_id=data.parent_id, sort_order=data.sort_order,
        shop_id=shop_ids[0],
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return CategoryResponse.model_validate(category)


@router.put("/categories/{category_id}", response_model=MessageResponse)
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update category."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cat, field, value)
    db.add(cat)
    return MessageResponse(message="更新成功")


@router.delete("/categories/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete category."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")
    # 检查是否有子分类
    children = await db.execute(select(func.count()).where(Category.parent_id == category_id, Category.is_active == True))
    if children.scalar() > 0:
        raise HTTPException(status_code=400, detail="请先删除子分类")
    cat.is_active = False
    db.add(cat)
    return MessageResponse(message="删除成功")


# ============ Brands ============

@router.get("/brands", response_model=list[BrandResponse])
async def list_brands(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List all brands."""
    result = await db.execute(
        select(ProductBrand).where(ProductBrand.shop_id.in_(shop_ids), ProductBrand.is_active == True).order_by(ProductBrand.created_at.desc())
    )
    return [BrandResponse.model_validate(b) for b in result.scalars().all()]


@router.post("/brands", response_model=BrandResponse)
async def create_brand(
    data: BrandCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a brand."""
    brand = ProductBrand(name=data.name, shop_id=shop_ids[0])
    db.add(brand)
    await db.flush()
    await db.refresh(brand)
    return BrandResponse.model_validate(brand)


@router.delete("/brands/{brand_id}", response_model=MessageResponse)
async def delete_brand(
    brand_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete brand."""
    result = await db.execute(select(ProductBrand).where(ProductBrand.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")
    brand.is_active = False
    db.add(brand)
    return MessageResponse(message="删除成功")


# ============ Product Units ============

@router.get("/product-units", response_model=list[ProductUnitResponse])
async def list_product_units(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List all product units."""
    result = await db.execute(
        select(ProductUnit).where(ProductUnit.shop_id.in_(shop_ids), ProductUnit.is_active == True)
    )
    return [ProductUnitResponse.model_validate(u) for u in result.scalars().all()]


@router.post("/product-units", response_model=ProductUnitResponse)
async def create_product_unit(
    data: ProductUnitCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a product unit."""
    unit = ProductUnit(name=data.name, shop_id=shop_ids[0])
    db.add(unit)
    await db.flush()
    await db.refresh(unit)
    return ProductUnitResponse.model_validate(unit)


@router.delete("/product-units/{unit_id}", response_model=MessageResponse)
async def delete_product_unit(
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete product unit."""
    result = await db.execute(select(ProductUnit).where(ProductUnit.id == unit_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="单位不存在")
    unit.is_active = False
    db.add(unit)
    return MessageResponse(message="删除成功")


# ============ Service Projects ============

@router.get("/projects", response_model=PaginatedResponse[ServiceProjectResponse])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: Optional[UUID] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated service project list."""
    query = (
        select(ServiceProject)
        .where(ServiceProject.shop_id.in_(shop_ids))
        .options(selectinload(ServiceProject.category), selectinload(ServiceProject.linked_products).selectinload(ProjectProduct.product))
    )
    if is_active is not None:
        query = query.where(ServiceProject.is_active == is_active)
    if category_id:
        query = query.where(ServiceProject.category_id == category_id)
    if search:
        query = query.where(ServiceProject.name.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(ServiceProject.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    projects = result.scalars().unique().all()
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[_build_project_response(p) for p in projects],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("/projects", response_model=ServiceProjectResponse)
async def create_project(
    data: ServiceProjectCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a new service project."""
    project = ServiceProject(
        name=data.name, category_id=data.category_id,
        price=data.price, member_price=data.member_price,
        duration=data.duration, description=data.description,
        commission_rate=data.commission_rate,
        commission_amount=data.commission_amount,
        image_url=data.image_url, shop_id=shop_ids[0],
    )
    db.add(project)
    await db.flush()

    # 关联产品
    if data.product_ids:
        for pid in data.product_ids:
            db.add(ProjectProduct(project_id=project.id, product_id=pid, quantity=1))
        await db.flush()

    # 重新查询以加载关联关系
    result = await db.execute(
        select(ServiceProject)
        .where(ServiceProject.id == project.id)
        .options(selectinload(ServiceProject.category), selectinload(ServiceProject.linked_products).selectinload(ProjectProduct.product))
    )
    project = result.scalar_one()
    return _build_project_response(project)


@router.get("/projects/{project_id}", response_model=ServiceProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get project detail."""
    result = await db.execute(
        select(ServiceProject)
        .where(ServiceProject.id == project_id)
        .options(selectinload(ServiceProject.category), selectinload(ServiceProject.linked_products).selectinload(ProjectProduct.product))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return _build_project_response(project)


@router.put("/projects/{project_id}", response_model=MessageResponse)
async def update_project(
    project_id: UUID,
    data: ServiceProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update project info."""
    result = await db.execute(select(ServiceProject).where(ServiceProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    update_data = data.model_dump(exclude_unset=True)
    product_ids = update_data.pop("product_ids", None)
    for field, value in update_data.items():
        setattr(project, field, value)
    db.add(project)

    # 更新关联产品
    if product_ids is not None:
        await db.execute(delete(ProjectProduct).where(ProjectProduct.project_id == project_id))
        for pid in product_ids:
            db.add(ProjectProduct(project_id=project_id, product_id=pid, quantity=1))

    return MessageResponse(message="更新成功")


@router.put("/projects/{project_id}/status", response_model=MessageResponse)
async def update_project_status(
    project_id: UUID,
    data: ProjectStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Toggle project active status (上架/下架)."""
    result = await db.execute(select(ServiceProject).where(ServiceProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    project.is_active = data.is_active
    db.add(project)
    status_text = "上架" if data.is_active else "下架"
    return MessageResponse(message=f"{status_text}成功")


@router.delete("/projects/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete project."""
    result = await db.execute(select(ServiceProject).where(ServiceProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    project.is_active = False
    db.add(project)
    return MessageResponse(message="删除成功")


# ============ Products ============

@router.get("/products", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: Optional[UUID] = None,
    brand_id: Optional[UUID] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated product list."""
    query = (
        select(Product)
        .where(Product.shop_id.in_(shop_ids))
        .options(selectinload(Product.category))
    )
    if is_active is not None:
        query = query.where(Product.is_active == is_active)
    if category_id:
        query = query.where(Product.category_id == category_id)
    if brand_id:
        query = query.where(Product.brand_id == brand_id)
    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Product.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    products = result.scalars().unique().all()
    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[_build_product_response(p) for p in products],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("/products", response_model=ProductResponse)
async def create_product(
    data: ProductCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a new product."""
    # 获取品牌名和单位名
    brand_name = None
    unit_name = None
    if data.brand_id:
        r = await db.execute(select(ProductBrand).where(ProductBrand.id == data.brand_id))
        brand = r.scalar_one_or_none()
        if brand:
            brand_name = brand.name
    if data.unit_id:
        r = await db.execute(select(ProductUnit).where(ProductUnit.id == data.unit_id))
        unit = r.scalar_one_or_none()
        if unit:
            unit_name = unit.name

    product = Product(
        name=data.name, brand_id=data.brand_id, brand_name=brand_name,
        category_id=data.category_id, image_url=data.image_url,
        sell_price=data.sell_price, cost_price=data.cost_price,
        spec=data.spec, unit_id=data.unit_id, unit_name=unit_name,
        barcode=data.barcode, stock_quantity=data.stock_quantity,
        stock_alert_value=data.stock_alert_value,
        shelf_life_days=data.shelf_life_days,
        expire_date=data.expire_date,
        deduct_stock=data.deduct_stock,
        description=data.description, shop_id=shop_ids[0],
    )
    db.add(product)
    await db.flush()

    # 初始化库存记录
    if data.stock_quantity > 0:
        inv = Inventory(product_id=product.id, shop_id=shop_ids[0], quantity=data.stock_quantity, last_inbound_at=datetime.utcnow())
        db.add(inv)

    await db.refresh(product, ["category"])
    return _build_product_response(product)


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get product detail."""
    result = await db.execute(
        select(Product).where(Product.id == product_id).options(selectinload(Product.category))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    return _build_product_response(product)


@router.put("/products/{product_id}", response_model=MessageResponse)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update product info."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    update_data = data.model_dump(exclude_unset=True)
    # 更新品牌名/单位名
    if "brand_id" in update_data and update_data["brand_id"]:
        r = await db.execute(select(ProductBrand).where(ProductBrand.id == update_data["brand_id"]))
        brand = r.scalar_one_or_none()
        if brand:
            update_data["brand_name"] = brand.name
    if "unit_id" in update_data and update_data["unit_id"]:
        r = await db.execute(select(ProductUnit).where(ProductUnit.id == update_data["unit_id"]))
        unit = r.scalar_one_or_none()
        if unit:
            update_data["unit_name"] = unit.name

    for field, value in update_data.items():
        setattr(product, field, value)
    db.add(product)
    return MessageResponse(message="更新成功")


@router.put("/products/{product_id}/status", response_model=MessageResponse)
async def update_product_status(
    product_id: UUID,
    data: ProjectStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Toggle product active status (上架/下架)."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    product.is_active = data.is_active
    db.add(product)
    status_text = "上架" if data.is_active else "下架"
    return MessageResponse(message=f"{status_text}成功")


@router.delete("/products/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    product.is_active = False
    db.add(product)
    return MessageResponse(message="删除成功")


# ============ Inventory ============

@router.get("/inventory", response_model=PaginatedResponse[InventoryResponse])
async def list_inventory(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get inventory list."""
    query = (
        select(Inventory)
        .where(Inventory.shop_id.in_(shop_ids))
        .options(selectinload(Inventory.product))
    )
    if search:
        # 需要join product来搜索
        query = query.join(Product).where(Product.name.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Inventory.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().unique().all()
    total_pages = (total + page_size - 1) // page_size

    inv_items = []
    for inv in items:
        prod = getattr(inv, "product", None)
        inv_items.append(InventoryResponse(
            id=inv.id, product_id=inv.product_id,
            product_name=prod.name if prod else None,
            brand_name=prod.brand_name if prod else None,
            quantity=inv.quantity,
            stock_alert_value=prod.stock_alert_value if prod else None,
            expire_date=prod.expire_date if prod else None,
            last_inbound_at=inv.last_inbound_at,
            last_outbound_at=inv.last_outbound_at,
        ))

    return PaginatedResponse(
        items=inv_items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


@router.get("/inventory/total")
async def inventory_total(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get inventory summary statistics."""
    total_items = await db.execute(
        select(func.count()).select_from(Inventory).where(Inventory.shop_id.in_(shop_ids))
    )
    total_quantity = await db.execute(
        select(func.sum(Inventory.quantity)).where(Inventory.shop_id.in_(shop_ids))
    )
    low_stock = await db.execute(
        select(func.count())
        .select_from(Inventory)
        .join(Product, Inventory.product_id == Product.id)
        .where(
            Inventory.shop_id.in_(shop_ids),
            Product.stock_alert_value.isnot(None),
            Inventory.quantity <= Product.stock_alert_value,
        )
    )

    return {
        "total_items": total_items.scalar() or 0,
        "total_quantity": total_quantity.scalar() or 0,
        "low_stock_count": low_stock.scalar() or 0,
    }


@router.post("/inventory/operate", response_model=MessageResponse)
async def operate_inventory(
    data: InventoryOperation,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Operate inventory (inbound/outbound/adjust/return)."""
    # 获取或创建库存记录
    result = await db.execute(
        select(Inventory).where(Inventory.product_id == data.product_id, Inventory.shop_id.in_(shop_ids))
    )
    inv = result.scalar_one_or_none()

    # 获取产品信息
    prod_result = await db.execute(select(Product).where(Product.id == data.product_id))
    product = prod_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    current_qty = inv.quantity if inv else 0

    if data.change_type == "inbound":
        new_qty = current_qty + data.quantity
    elif data.change_type in ("outbound", "return"):
        new_qty = current_qty - data.quantity
        if new_qty < 0:
            raise HTTPException(status_code=400, detail="库存不足")
    elif data.change_type == "adjust":
        new_qty = data.quantity  # 直接设置
    else:
        raise HTTPException(status_code=400, detail="无效的操作类型")

    # 更新库存
    if inv:
        inv.quantity = new_qty
        if data.change_type == "inbound":
            inv.last_inbound_at = datetime.utcnow()
        elif data.change_type in ("outbound", "return"):
            inv.last_outbound_at = datetime.utcnow()
    else:
        inv = Inventory(
            product_id=data.product_id, shop_id=shop_ids[0],
            quantity=new_qty,
            last_inbound_at=datetime.utcnow() if data.change_type == "inbound" else None,
        )
        db.add(inv)

    # 记录日志
    change_qty = data.quantity if data.change_type in ("inbound", "return") else -data.quantity
    if data.change_type == "adjust":
        change_qty = new_qty - current_qty
    log = InventoryLog(
        product_id=data.product_id, shop_id=shop_ids[0],
        change_type=data.change_type, change_quantity=change_qty,
        before_quantity=current_qty, after_quantity=new_qty,
        reason=data.reason,
    )
    db.add(log)

    # 同步product表库存
    product.stock_quantity = new_qty
    db.add(product)

    return MessageResponse(message="操作成功")


@router.post("/inventory/batch-operate", response_model=MessageResponse)
async def batch_operate_inventory(
    data: InventoryBatchOperation,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Batch inventory operations."""
    for op in data.operations:
        await operate_inventory(op, shop_id=shop_ids[0], db=db)
    return MessageResponse(message=f"批量操作成功，共{len(data.operations)}项")


@router.get("/inventory/logs", response_model=PaginatedResponse[InventoryLogResponse])
async def list_inventory_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_id: Optional[UUID] = None,
    change_type: Optional[str] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get inventory change logs."""
    query = (
        select(InventoryLog)
        .where(InventoryLog.shop_id.in_(shop_ids))
        .options(selectinload(InventoryLog.product))
    )
    if product_id:
        query = query.where(InventoryLog.product_id == product_id)
    if change_type:
        query = query.where(InventoryLog.change_type == change_type)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(InventoryLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().unique().all()
    total_pages = (total + page_size - 1) // page_size

    items = []
    for log in logs:
        prod = getattr(log, "product", None)
        items.append(InventoryLogResponse(
            id=log.id, product_id=log.product_id,
            product_name=prod.name if prod else None,
            change_type=log.change_type, change_quantity=log.change_quantity,
            before_quantity=log.before_quantity, after_quantity=log.after_quantity,
            reason=log.reason, operator_id=log.operator_id,
            created_at=log.created_at,
        ))

    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


@router.get("/inventory/alerts", response_model=list[StockAlertItem])
async def get_stock_alerts(
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get stock alerts (low stock and expiring products)."""
    alerts = []

    # 低库存预警
    low_stock_result = await db.execute(
        select(Product).where(
            Product.shop_id.in_(shop_ids),
            Product.is_active == True,
            Product.stock_alert_value.isnot(None),
            Product.stock_quantity <= Product.stock_alert_value,
        )
    )
    for p in low_stock_result.scalars().all():
        alerts.append(StockAlertItem(
            product_id=p.id, product_name=p.name,
            stock_quantity=p.stock_quantity,
            stock_alert_value=p.stock_alert_value or 0,
            alert_type="low_stock",
        ))

    # 保质期预警（30天内到期）
    threshold = datetime.utcnow().date() + timedelta(days=30)
    expiring_result = await db.execute(
        select(Product).where(
            Product.shop_id.in_(shop_ids),
            Product.is_active == True,
            Product.expire_date.isnot(None),
            Product.expire_date <= threshold,
        )
    )
    for p in expiring_result.scalars().all():
        alerts.append(StockAlertItem(
            product_id=p.id, product_name=p.name,
            stock_quantity=p.stock_quantity,
            stock_alert_value=p.stock_alert_value or 0,
            alert_type="expiring",
        ))

    return alerts


# ============ Tickets ============

@router.get("/tickets", response_model=PaginatedResponse[TicketResponse])
async def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated ticket list."""
    query = (
        select(Ticket)
        .where(Ticket.shop_id.in_(shop_ids))
        .options(selectinload(Ticket.project))
    )
    if is_active is not None:
        query = query.where(Ticket.is_active == is_active)
    if search:
        query = query.where(Ticket.name.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Ticket.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tickets = result.scalars().unique().all()
    total_pages = (total + page_size - 1) // page_size

    items = []
    for t in tickets:
        proj = getattr(t, "project", None)
        items.append(TicketResponse(
            id=t.id, name=t.name, project_id=t.project_id,
            project_name=proj.name if proj else None,
            total_count=t.total_count, price=float(t.price),
            original_price=float(t.original_price) if t.original_price else None,
            valid_days=t.valid_days, description=t.description,
            is_active=t.is_active, created_at=t.created_at,
        ))

    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(
    data: TicketCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a ticket."""
    ticket = Ticket(
        name=data.name, project_id=data.project_id,
        total_count=data.total_count, price=data.price,
        original_price=data.original_price,
        valid_days=data.valid_days, description=data.description,
        shop_id=shop_ids[0],
    )
    db.add(ticket)
    await db.flush()
    await db.refresh(ticket, ["project"])

    proj = getattr(ticket, "project", None)
    return TicketResponse(
        id=ticket.id, name=ticket.name, project_id=ticket.project_id,
        project_name=proj.name if proj else None,
        total_count=ticket.total_count, price=float(ticket.price),
        original_price=float(ticket.original_price) if ticket.original_price else None,
        valid_days=ticket.valid_days, description=ticket.description,
        is_active=ticket.is_active, created_at=ticket.created_at,
    )


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get ticket detail."""
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id).options(selectinload(Ticket.project))
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="次券不存在")
    proj = getattr(ticket, "project", None)
    return TicketResponse(
        id=ticket.id, name=ticket.name, project_id=ticket.project_id,
        project_name=proj.name if proj else None,
        total_count=ticket.total_count, price=float(ticket.price),
        original_price=float(ticket.original_price) if ticket.original_price else None,
        valid_days=ticket.valid_days, description=ticket.description,
        is_active=ticket.is_active, created_at=ticket.created_at,
    )


@router.put("/tickets/{ticket_id}", response_model=MessageResponse)
async def update_ticket(
    ticket_id: UUID,
    data: TicketUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update ticket."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="次券不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    db.add(ticket)
    return MessageResponse(message="更新成功")


@router.delete("/tickets/{ticket_id}", response_model=MessageResponse)
async def delete_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete ticket."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="次券不存在")
    ticket.is_active = False
    db.add(ticket)
    return MessageResponse(message="删除成功")


# ============ Price Templates ============

@router.get("/price-templates", response_model=list[PriceTemplateResponse])
async def list_price_templates(
    item_type: Optional[str] = None,
    item_id: Optional[UUID] = None,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """List price templates."""
    query = select(PriceTemplate).where(PriceTemplate.shop_id.in_(shop_ids))
    if item_type:
        query = query.where(PriceTemplate.item_type == item_type)
    if item_id:
        query = query.where(PriceTemplate.item_id == item_id)
    result = await db.execute(query.order_by(PriceTemplate.created_at.desc()))
    return [PriceTemplateResponse.model_validate(t) for t in result.scalars().all()]


@router.post("/price-templates", response_model=PriceTemplateResponse)
async def create_price_template(
    data: PriceTemplateCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Create a price template."""
    template = PriceTemplate(
        name=data.name, item_type=data.item_type,
        item_id=data.item_id, level_name=data.level_name,
        price=data.price, shop_id=shop_ids[0],
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return PriceTemplateResponse.model_validate(template)


@router.post("/price-templates/batch", response_model=MessageResponse)
async def batch_create_price_templates(
    data: PriceTemplateBatchCreate,
    shop_ids: list[UUID] = Depends(get_effective_shop_ids),
    db: AsyncSession = Depends(get_db),
):
    """Batch create price templates for an item."""
    # 先删除该item的旧模板
    await db.execute(
        delete(PriceTemplate).where(
            PriceTemplate.shop_id.in_(shop_ids),
            PriceTemplate.item_type == data.item_type,
            PriceTemplate.item_id == data.item_id,
        )
    )
    # 批量创建
    for p in data.prices:
        template = PriceTemplate(
            name=f"{data.item_type}_template",
            item_type=data.item_type, item_id=data.item_id,
            level_name=p["level_name"], price=p["price"],
            shop_id=shop_ids[0],
        )
        db.add(template)
    return MessageResponse(message=f"批量创建成功，共{len(data.prices)}条")
