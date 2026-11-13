"""Seed data script - creates initial data for demo."""
import asyncio
from datetime import datetime, date, timedelta
from uuid import uuid4
from passlib.context import CryptContext

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models.shop import Shop, Room
from app.models.staff import Staff, Position
from app.models.customer import Customer, Tag, Source
from app.models.card import CardType, MemberCard
from app.models.order import Order, OrderItem, Payment, PaymentMethod
from app.models.item import ServiceProject, Product, Category

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Use sync engine for seeding
engine = create_engine(settings.database_url_sync)
SessionLocal = sessionmaker(bind=engine)


def seed_data():
    """Create all tables and insert seed data."""
    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Check if data already exists
        if db.query(Shop).count() > 0:
            print("Seed data already exists, skipping...")
            return

        # === Shop ===
        shop = Shop(
            id=uuid4(),
            name="余几美雕科技皮肤管理",
            code="SHOP001",
            address="上海市浦东新区世纪大道100号",
            phone="021-12345678",
            is_active=True,
        )
        db.add(shop)
        db.flush()

        # === Rooms ===
        rooms = [
            Room(id=uuid4(), shop_id=shop.id, name="VIP室1", beds=1, floor=1, is_active=True),
            Room(id=uuid4(), shop_id=shop.id, name="VIP室2", beds=1, floor=1, is_active=True),
            Room(id=uuid4(), shop_id=shop.id, name="普通室1", beds=2, floor=2, is_active=True),
            Room(id=uuid4(), shop_id=shop.id, name="普通室2", beds=2, floor=2, is_active=True),
        ]
        db.add_all(rooms)

        # === Positions ===
        positions = [
            Position(id=uuid4(), name="店长", sort_order=1),
            Position(id=uuid4(), name="美容师", sort_order=2),
            Position(id=uuid4(), name="技师", sort_order=3),
            Position(id=uuid4(), name="前台", sort_order=4),
            Position(id=uuid4(), name="收银员", sort_order=5),
        ]
        db.add_all(positions)
        db.flush()

        # === Staff (admin account) ===
        admin = Staff(
            id=uuid4(),
            name="店长",
            phone="13800138000",
            password_hash=pwd_context.hash("123456"),
            shop_id=shop.id,
            position_id=positions[0].id,
            role="admin",
            is_active=True,
            hire_date=datetime(2023, 1, 1),
        )
        staff_list = [
            Staff(
                id=uuid4(),
                name="李美容师",
                phone="13800138001",
                password_hash=pwd_context.hash("123456"),
                shop_id=shop.id,
                position_id=positions[1].id,
                role="staff",
                is_active=True,
                hire_date=datetime(2023, 3, 1),
            ),
            Staff(
                id=uuid4(),
                name="王技师",
                phone="13800138002",
                password_hash=pwd_context.hash("123456"),
                shop_id=shop.id,
                position_id=positions[2].id,
                role="staff",
                is_active=True,
                hire_date=datetime(2023, 6, 1),
            ),
            Staff(
                id=uuid4(),
                name="陈前台",
                phone="13800138003",
                password_hash=pwd_context.hash("123456"),
                shop_id=shop.id,
                position_id=positions[3].id,
                role="staff",
                is_active=True,
                hire_date=datetime(2024, 1, 1),
            ),
        ]
        db.add(admin)
        db.add_all(staff_list)
        db.flush()

        # === Tags ===
        tags = [
            Tag(id=uuid4(), name="VIP", color="#FF6B8A", shop_id=shop.id),
            Tag(id=uuid4(), name="新客", color="#4CAF50", shop_id=shop.id),
            Tag(id=uuid4(), name="高消费", color="#FF9800", shop_id=shop.id),
            Tag(id=uuid4(), name="敏感肌", color="#9C27B0", shop_id=shop.id),
            Tag(id=uuid4(), name="需回访", color="#2196F3", shop_id=shop.id),
        ]
        db.add_all(tags)

        # === Sources ===
        sources = [
            Source(id=uuid4(), name="自然到店", shop_id=shop.id),
            Source(id=uuid4(), name="朋友推荐", shop_id=shop.id),
            Source(id=uuid4(), name="美团", shop_id=shop.id),
            Source(id=uuid4(), name="抖音", shop_id=shop.id),
            Source(id=uuid4(), name="大众点评", shop_id=shop.id),
            Source(id=uuid4(), name="微信公众号", shop_id=shop.id),
        ]
        db.add_all(sources)
        db.flush()

        # === Customers ===
        customers = [
            Customer(
                id=uuid4(), name="张美丽", code="C0001", phone="13812341234",
                gender="female", birthday=date(1990, 5, 20),
                shop_id=shop.id, source_id=sources[0].id, staff_id=staff_list[0].id,
                level="gold", balance=3580.0, points=2580, total_consumption=12800.0,
                last_visit_at=datetime(2024, 10, 8), remark="喜欢深层清洁项目",
            ),
            Customer(
                id=uuid4(), name="王芳芳", code="C0002", phone="13956785678",
                gender="female", birthday=date(1988, 11, 15),
                shop_id=shop.id, source_id=sources[1].id, staff_id=staff_list[1].id,
                level="silver", balance=1200.0, points=1200, total_consumption=5600.0,
                last_visit_at=datetime(2024, 10, 7),
            ),
            Customer(
                id=uuid4(), name="李雅婷", code="C0003", phone="13790129012",
                gender="female", birthday=date(1992, 3, 8),
                shop_id=shop.id, source_id=sources[2].id, staff_id=staff_list[0].id,
                level="platinum", balance=5000.0, points=4500, total_consumption=25000.0,
                last_visit_at=datetime(2024, 10, 6), taboo="对酒精过敏",
            ),
            Customer(
                id=uuid4(), name="陈雪梅", code="C0004", phone="13634563456",
                gender="female", birthday=date(1985, 7, 22),
                shop_id=shop.id, source_id=sources[3].id,
                level="normal", balance=0.0, points=500, total_consumption=3000.0,
                last_visit_at=datetime(2024, 9, 30),
            ),
            Customer(
                id=uuid4(), name="刘晓燕", code="C0005", phone="13578907890",
                gender="female", birthday=date(1995, 12, 25),
                shop_id=shop.id, source_id=sources[0].id, staff_id=staff_list[0].id,
                level="diamond", balance=8000.0, points=8000, total_consumption=35000.0,
                last_visit_at=datetime(2024, 10, 9), remark="每月固定来做面部护理",
            ),
        ]
        db.add_all(customers)

        # === Categories ===
        cat_face = Category(id=uuid4(), name="面部护理", category_type="project", shop_id=shop.id, sort_order=1)
        cat_body = Category(id=uuid4(), name="身体护理", category_type="project", shop_id=shop.id, sort_order=2)
        cat_nail = Category(id=uuid4(), name="美甲美睫", category_type="project", shop_id=shop.id, sort_order=3)
        db.add_all([cat_face, cat_body, cat_nail])
        db.flush()

        # === Service Projects ===
        projects = [
            ServiceProject(id=uuid4(), name="深层清洁", category_id=cat_face.id, price=298.0, member_price=258.0, duration=60, shop_id=shop.id, commission_rate=10.0),
            ServiceProject(id=uuid4(), name="面部护理", category_id=cat_face.id, price=398.0, member_price=348.0, duration=90, shop_id=shop.id, commission_rate=12.0),
            ServiceProject(id=uuid4(), name="补水保湿", category_id=cat_face.id, price=268.0, member_price=228.0, duration=45, shop_id=shop.id, commission_rate=10.0),
            ServiceProject(id=uuid4(), name="全身SPA", category_id=cat_body.id, price=998.0, member_price=888.0, duration=120, shop_id=shop.id, commission_rate=15.0),
            ServiceProject(id=uuid4(), name="精油推拿", category_id=cat_body.id, price=598.0, member_price=498.0, duration=90, shop_id=shop.id, commission_rate=12.0),
            ServiceProject(id=uuid4(), name="美甲", category_id=cat_nail.id, price=198.0, member_price=168.0, duration=60, shop_id=shop.id, commission_rate=8.0),
            ServiceProject(id=uuid4(), name="美睫", category_id=cat_nail.id, price=298.0, member_price=258.0, duration=45, shop_id=shop.id, commission_rate=10.0),
        ]
        db.add_all(projects)

        # === Payment Methods ===
        payment_methods = [
            PaymentMethod(id=uuid4(), name="现金", sort_order=1, shop_id=shop.id),
            PaymentMethod(id=uuid4(), name="微信支付", sort_order=2, shop_id=shop.id),
            PaymentMethod(id=uuid4(), name="支付宝", sort_order=3, shop_id=shop.id),
            PaymentMethod(id=uuid4(), name="刷卡", sort_order=4, shop_id=shop.id),
            PaymentMethod(id=uuid4(), name="储值卡", sort_order=5, shop_id=shop.id),
            PaymentMethod(id=uuid4(), name="次卡抵扣", sort_order=6, shop_id=shop.id),
        ]
        db.add_all(payment_methods)

        # === Card Types ===
        card_types = [
            CardType(
                id=uuid4(), name="银卡储值", card_category="stored_value",
                sell_price=1000.0, face_value=1000.0, present_amount=100.0,
                validity_type="permanent", shop_id=shop.id,
                description="充值1000送100",
            ),
            CardType(
                id=uuid4(), name="金卡储值", card_category="stored_value",
                sell_price=3000.0, face_value=3000.0, present_amount=500.0,
                validity_type="permanent", shop_id=shop.id,
                description="充值3000送500",
            ),
            CardType(
                id=uuid4(), name="面部护理10次卡", card_category="times",
                sell_price=3000.0, face_value=3980.0,
                validity_type="days", validity_days=365, shop_id=shop.id,
                description="面部护理10次，有效期1年",
            ),
        ]
        db.add_all(card_types)

        db.commit()
        print("Seed data created successfully!")
        print(f"  - Shop: {shop.name}")
        print(f"  - Admin: 13800138000 / 123456")
        print(f"  - Staff: {len(staff_list)} members")
        print(f"  - Customers: {len(customers)}")
        print(f"  - Projects: {len(projects)}")
        print(f"  - Card Types: {len(card_types)}")

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
