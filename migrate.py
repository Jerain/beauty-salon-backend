import asyncio
from app.database import engine
from sqlalchemy import text

async def migrate():
    async with engine.begin() as conn:
        # 添加 orders 表的新列
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS hold_status VARCHAR(20)"))
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS refund_reason TEXT"))
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS refund_type VARCHAR(20)"))
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS refund_amount NUMERIC(12,2) DEFAULT 0.0"))
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS refund_method VARCHAR(50)"))
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS verify_status VARCHAR(20) DEFAULT 'unverified'"))
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS verify_at TIMESTAMP"))
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS updated_by UUID"))
        
        # 添加 payments 表的新列
        await conn.execute(text("ALTER TABLE payments ADD COLUMN IF NOT EXISTS is_arrears BOOLEAN DEFAULT FALSE"))
        
        # 创建 order_records 表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS order_records (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                action VARCHAR(50) NOT NULL,
                old_status VARCHAR(20),
                new_status VARCHAR(20),
                remark TEXT,
                created_by UUID REFERENCES staff(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        print("Migration completed!")

asyncio.run(migrate())
