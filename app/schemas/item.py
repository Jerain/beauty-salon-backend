"""Item (ServiceProject/Product/Category/Inventory/Brand/Unit/Ticket) schemas."""
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel


# ============ Category ============

class CategoryResponse(BaseModel):
    id: UUID
    name: str
    category_type: str
    sort_order: int
    parent_id: UUID | None = None

    model_config = {"from_attributes": True}


class CategoryTreeResponse(BaseModel):
    id: UUID
    name: str
    category_type: str
    sort_order: int
    children: list["CategoryTreeResponse"] = []

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str
    category_type: str = "project"
    parent_id: UUID | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    parent_id: UUID | None = None


# ============ Brand ============

class BrandResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BrandCreate(BaseModel):
    name: str


# ============ ProductUnit ============

class ProductUnitResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductUnitCreate(BaseModel):
    name: str


# ============ ServiceProject ============

class ProjectProductItem(BaseModel):
    product_id: UUID
    product_name: str | None = None
    quantity: int = 1

    model_config = {"from_attributes": True}


class ServiceProjectResponse(BaseModel):
    id: UUID
    name: str
    category_id: UUID | None = None
    category_name: str | None = None
    image_url: str | None = None
    price: float
    member_price: float | None = None
    duration: int
    description: str | None = None
    commission_rate: float | None = None
    commission_amount: float | None = None
    shop_id: UUID | None = None
    is_active: bool
    created_at: datetime
    linked_products: list[ProjectProductItem] = []

    model_config = {"from_attributes": True}


class ServiceProjectCreate(BaseModel):
    name: str
    category_id: UUID | None = None
    price: float
    member_price: float | None = None
    duration: int = 60
    description: str | None = None
    commission_rate: float | None = None
    commission_amount: float | None = None
    image_url: str | None = None
    product_ids: list[UUID] = []  # 关联产品ID列表


class ServiceProjectUpdate(BaseModel):
    name: str | None = None
    category_id: UUID | None = None
    price: float | None = None
    member_price: float | None = None
    duration: int | None = None
    description: str | None = None
    commission_rate: float | None = None
    commission_amount: float | None = None
    is_active: bool | None = None
    image_url: str | None = None
    product_ids: list[UUID] | None = None  # 更新关联产品


class ProjectStatusUpdate(BaseModel):
    is_active: bool


# ============ Product ============

class ProductResponse(BaseModel):
    id: UUID
    name: str
    brand_id: UUID | None = None
    brand_name: str | None = None
    category_id: UUID | None = None
    category_name: str | None = None
    image_url: str | None = None
    sell_price: float
    cost_price: float | None = None
    spec: str | None = None
    unit_id: UUID | None = None
    unit_name: str | None = None
    barcode: str | None = None
    stock_quantity: int
    stock_alert_value: int | None = None
    shelf_life_days: int | None = None
    expire_date: date | None = None
    deduct_stock: bool
    description: str | None = None
    shop_id: UUID | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str
    brand_id: UUID | None = None
    category_id: UUID | None = None
    sell_price: float
    cost_price: float | None = None
    spec: str | None = None
    unit_id: UUID | None = None
    barcode: str | None = None
    stock_quantity: int = 0
    stock_alert_value: int | None = None
    shelf_life_days: int | None = None
    expire_date: date | None = None
    deduct_stock: bool = True
    description: str | None = None
    image_url: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    brand_id: UUID | None = None
    category_id: UUID | None = None
    sell_price: float | None = None
    cost_price: float | None = None
    spec: str | None = None
    unit_id: UUID | None = None
    barcode: str | None = None
    stock_alert_value: int | None = None
    shelf_life_days: int | None = None
    expire_date: date | None = None
    deduct_stock: bool | None = None
    description: str | None = None
    is_active: bool | None = None
    image_url: str | None = None


# ============ Inventory ============

class InventoryResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str | None = None
    brand_name: str | None = None
    quantity: int
    stock_alert_value: int | None = None
    expire_date: date | None = None
    last_inbound_at: datetime | None = None
    last_outbound_at: datetime | None = None

    model_config = {"from_attributes": True}


class InventoryLogResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str | None = None
    change_type: str
    change_quantity: int
    before_quantity: int
    after_quantity: int
    reason: str | None = None
    operator_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InventoryOperation(BaseModel):
    product_id: UUID
    change_type: str  # inbound/outbound/adjust/return
    quantity: int  # 正数
    reason: str | None = None


class InventoryBatchOperation(BaseModel):
    operations: list[InventoryOperation]


class StockAlertItem(BaseModel):
    product_id: UUID
    product_name: str
    stock_quantity: int
    stock_alert_value: int
    alert_type: str  # low_stock/expiring

    model_config = {"from_attributes": True}


# ============ Ticket ============

class TicketResponse(BaseModel):
    id: UUID
    name: str
    project_id: UUID | None = None
    project_name: str | None = None
    total_count: int
    price: float
    original_price: float | None = None
    valid_days: int
    description: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketCreate(BaseModel):
    name: str
    project_id: UUID | None = None
    total_count: int = 1
    price: float
    original_price: float | None = None
    valid_days: int = 30
    description: str | None = None


class TicketUpdate(BaseModel):
    name: str | None = None
    project_id: UUID | None = None
    total_count: int | None = None
    price: float | None = None
    original_price: float | None = None
    valid_days: int | None = None
    description: str | None = None
    is_active: bool | None = None


# ============ PriceTemplate ============

class PriceTemplateResponse(BaseModel):
    id: UUID
    name: str
    item_type: str
    item_id: UUID
    level_name: str
    price: float
    created_at: datetime

    model_config = {"from_attributes": True}


class PriceTemplateCreate(BaseModel):
    name: str
    item_type: str  # project/product
    item_id: UUID
    level_name: str
    price: float


class PriceTemplateBatchCreate(BaseModel):
    item_type: str
    item_id: UUID
    prices: list[dict]  # [{level_name: "普通会员", price: 100}, ...]
