"""ServiceProject, Product, Category, Inventory, Brand, Unit, Ticket models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Integer, Numeric, Date, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    category_type: Mapped[str] = mapped_column(String(20), default="project")  # project/product
    shop_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    children: Mapped[list["Category"]] = relationship(back_populates="parent")
    parent: Mapped["Category | None"] = relationship(back_populates="children", remote_side=[id])


class ProductBrand(Base):
    """产品品牌"""
    __tablename__ = "product_brands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProductUnit(Base):
    """产品单位/规格"""
    __tablename__ = "product_units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ServiceProject(Base):
    __tablename__ = "service_projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    image_url: Mapped[str | None] = mapped_column(String(500))
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    member_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    duration: Mapped[int] = mapped_column(Integer, default=60)  # minutes
    description: Mapped[str | None] = mapped_column(Text)
    commission_rate: Mapped[float | None] = mapped_column(Numeric(5, 2))
    commission_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    shop_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category: Mapped["Category | None"] = relationship()
    # 关联产品列表
    linked_products: Mapped[list["ProjectProduct"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectProduct(Base):
    """项目-产品关联表"""
    __tablename__ = "project_products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("service_projects.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)  # 使用数量
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["ServiceProject"] = relationship(back_populates="linked_products")
    product: Mapped["Product"] = relationship()


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"))
    brand_name: Mapped[str | None] = mapped_column(String(50))  # 冗余字段，便于查询
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    image_url: Mapped[str | None] = mapped_column(String(500))
    sell_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    cost_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    spec: Mapped[str | None] = mapped_column(String(100))
    unit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("product_units.id"))
    unit_name: Mapped[str | None] = mapped_column(String(20))  # 冗余
    barcode: Mapped[str | None] = mapped_column(String(50))
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    stock_alert_value: Mapped[int | None] = mapped_column(Integer)
    shelf_life_days: Mapped[int | None] = mapped_column(Integer)
    expire_date: Mapped[datetime | None] = mapped_column(Date)
    deduct_stock: Mapped[bool] = mapped_column(Boolean, default=True)  # 开单扣库存开关
    description: Mapped[str | None] = mapped_column(Text)
    shop_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category: Mapped["Category | None"] = relationship()
    brand: Mapped["Brand | None"] = relationship()
    unit: Mapped["ProductUnit | None"] = relationship()


class Inventory(Base):
    """库存记录（当前库存快照）"""
    __tablename__ = "inventory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    cost_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # 加权平均成本单价
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_outbound_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product: Mapped["Product"] = relationship()


class InventoryLog(Base):
    """库存变动日志"""
    __tablename__ = "inventory_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)  # inbound/outbound/adjust/return
    change_quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 正数入库，负数出库
    before_quantity: Mapped[int] = mapped_column(Integer, default=0)
    after_quantity: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str | None] = mapped_column(String(200))
    operator_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped["Product"] = relationship()


class StockOrder(Base):
    """入库/出库单据（主单）"""
    __tablename__ = "stock_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_no: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)  # 单据号
    order_type: Mapped[str] = mapped_column(String(10), nullable=False)  # inbound/outbound
    stock_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 采购/调拨/退单/盘盈/销售/盘亏/报损等
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    warehouse_name: Mapped[str | None] = mapped_column(String(50))
    operator_name: Mapped[str | None] = mapped_column(String(50))  # 经办人
    creator_name: Mapped[str | None] = mapped_column(String(50))  # 制单人
    supplier_name: Mapped[str | None] = mapped_column(String(100))  # 供应商（入库）
    customer_name: Mapped[str | None] = mapped_column(String(100))  # 客户（出库）
    remark: Mapped[str | None] = mapped_column(Text)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    order_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # 入库/出库时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items: Mapped[list["StockOrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class StockOrderItem(Base):
    """入库/出库单据明细行"""
    __tablename__ = "stock_order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_orders.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    product_name: Mapped[str | None] = mapped_column(String(100))
    product_code: Mapped[str | None] = mapped_column(String(50))
    brand_name: Mapped[str | None] = mapped_column(String(50))
    category_name: Mapped[str | None] = mapped_column(String(50))
    unit: Mapped[str | None] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    cost_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    cost_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    production_date: Mapped[datetime | None] = mapped_column(Date)
    shelf_life_months: Mapped[int | None] = mapped_column(Integer)
    expire_date: Mapped[datetime | None] = mapped_column(Date)
    batch_no: Mapped[str | None] = mapped_column(String(50))
    remark: Mapped[str | None] = mapped_column(String(200))

    order: Mapped["StockOrder"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


class CostAdjustment(Base):
    """成本调整记录"""
    __tablename__ = "cost_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_no: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    warehouse_name: Mapped[str | None] = mapped_column(String(50))
    operator_name: Mapped[str | None] = mapped_column(String(50))
    creator_name: Mapped[str | None] = mapped_column(String(50))
    remark: Mapped[str | None] = mapped_column(Text)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    items: Mapped[list["CostAdjustmentItem"]] = relationship(back_populates="adjustment", cascade="all, delete-orphan")


class CostAdjustmentItem(Base):
    """成本调整明细行"""
    __tablename__ = "cost_adjustment_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    adjustment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cost_adjustments.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    product_name: Mapped[str | None] = mapped_column(String(100))
    product_code: Mapped[str | None] = mapped_column(String(50))
    unit: Mapped[str | None] = mapped_column(String(20))
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    old_cost_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    new_cost_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    cost_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    remark: Mapped[str | None] = mapped_column(String(200))

    adjustment: Mapped["CostAdjustment"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


class Ticket(Base):
    """次券（体验券）"""
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("service_projects.id"))
    total_count: Mapped[int] = mapped_column(Integer, default=1)  # 可用次数
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)  # 售价
    original_price: Mapped[float | None] = mapped_column(Numeric(12, 2))  # 原价
    valid_days: Mapped[int] = mapped_column(Integer, default=30)  # 有效天数
    description: Mapped[str | None] = mapped_column(Text)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["ServiceProject | None"] = relationship()


class PriceTemplate(Base):
    """价格模板"""
    __tablename__ = "price_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)  # project/product
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    level_name: Mapped[str] = mapped_column(String(20), nullable=False)  # 会员等级名
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
