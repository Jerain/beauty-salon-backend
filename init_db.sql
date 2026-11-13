-- ============================================
-- Beauty Salon SaaS - Database Initialization
-- Generated for PostgreSQL 18
-- ============================================

BEGIN;

-- Enable uuid extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLE DEFINITIONS (matching SQLAlchemy models)
-- ============================================

-- 1. shops (门店)
CREATE TABLE IF NOT EXISTS shops (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    address TEXT,
    phone VARCHAR(20),
    logo_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. rooms (房间)
CREATE TABLE IF NOT EXISTS rooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shop_id UUID NOT NULL REFERENCES shops(id),
    name VARCHAR(100) NOT NULL,
    beds INTEGER DEFAULT 1,
    floor INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. positions (职位)
CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. staff (员工)
CREATE TABLE IF NOT EXISTS staff (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    shop_id UUID NOT NULL REFERENCES shops(id),
    position_id UUID REFERENCES positions(id),
    role VARCHAR(20) DEFAULT 'staff',
    is_active BOOLEAN DEFAULT TRUE,
    hire_date TIMESTAMP,
    points INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 5. sources (来源渠道)
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    shop_id UUID REFERENCES shops(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 6. tags (标签)
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    color VARCHAR(20),
    shop_id UUID REFERENCES shops(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 7. customers (顾客)
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    gender VARCHAR(10),
    birthday DATE,
    avatar_url VARCHAR(500),
    shop_id UUID NOT NULL REFERENCES shops(id),
    source_id UUID REFERENCES sources(id),
    staff_id UUID REFERENCES staff(id),
    level VARCHAR(20) DEFAULT 'normal',
    balance NUMERIC(12,2) DEFAULT 0.0,
    points INTEGER DEFAULT 0,
    total_consumption NUMERIC(12,2) DEFAULT 0.0,
    remark TEXT,
    taboo TEXT,
    last_visit_at TIMESTAMP,
    is_blacklisted BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 8. customer_tags (顾客-标签关联)
CREATE TABLE IF NOT EXISTS customer_tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    tag_id UUID NOT NULL REFERENCES tags(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 9. categories (分类)
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    parent_id UUID REFERENCES categories(id),
    sort_order INTEGER DEFAULT 0,
    category_type VARCHAR(20) DEFAULT 'project',
    shop_id UUID REFERENCES shops(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 10. service_projects (服务项目)
CREATE TABLE IF NOT EXISTS service_projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    category_id UUID REFERENCES categories(id),
    image_url VARCHAR(500),
    price NUMERIC(12,2) NOT NULL,
    member_price NUMERIC(12,2),
    duration INTEGER DEFAULT 60,
    description TEXT,
    commission_rate NUMERIC(5,2),
    shop_id UUID REFERENCES shops(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 11. products (产品)
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    brand VARCHAR(50),
    category_id UUID REFERENCES categories(id),
    image_url VARCHAR(500),
    sell_price NUMERIC(12,2) NOT NULL,
    cost_price NUMERIC(12,2),
    spec VARCHAR(100),
    unit VARCHAR(20),
    barcode VARCHAR(50),
    stock_quantity INTEGER DEFAULT 0,
    stock_alert_value INTEGER,
    shelf_life_days INTEGER,
    description TEXT,
    shop_id UUID REFERENCES shops(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 12. inventory (库存记录)
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id),
    shop_id UUID NOT NULL REFERENCES shops(id),
    quantity INTEGER DEFAULT 0,
    transaction_type VARCHAR(20) NOT NULL,
    change_quantity INTEGER NOT NULL,
    reason VARCHAR(200),
    operator_id UUID REFERENCES staff(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 13. card_types (卡类型)
CREATE TABLE IF NOT EXISTS card_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    card_category VARCHAR(20) NOT NULL,
    sell_price NUMERIC(12,2) NOT NULL,
    face_value NUMERIC(12,2) NOT NULL,
    present_amount NUMERIC(12,2) DEFAULT 0.0,
    present_items JSONB,
    validity_type VARCHAR(20) DEFAULT 'permanent',
    validity_days INTEGER,
    start_date DATE,
    end_date DATE,
    consume_rule JSONB,
    description TEXT,
    shop_id UUID REFERENCES shops(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 14. member_cards (会员卡)
CREATE TABLE IF NOT EXISTS member_cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    card_type_id UUID NOT NULL REFERENCES card_types(id),
    card_no VARCHAR(50) UNIQUE NOT NULL,
    principal_balance NUMERIC(12,2) DEFAULT 0.0,
    present_balance NUMERIC(12,2) DEFAULT 0.0,
    total_times INTEGER,
    remaining_times INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    activate_date TIMESTAMP DEFAULT NOW(),
    expire_date TIMESTAMP,
    remark TEXT,
    created_by UUID REFERENCES staff(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 15. payment_methods (支付方式)
CREATE TABLE IF NOT EXISTS payment_methods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    icon VARCHAR(50),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    shop_id UUID REFERENCES shops(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 16. orders (订单)
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_no VARCHAR(30) UNIQUE NOT NULL,
    customer_id UUID REFERENCES customers(id),
    shop_id UUID NOT NULL REFERENCES shops(id),
    total_amount NUMERIC(12,2) DEFAULT 0.0,
    discount_amount NUMERIC(12,2) DEFAULT 0.0,
    paid_amount NUMERIC(12,2) DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'pending',
    order_type VARCHAR(20) DEFAULT 'service',
    consume_type VARCHAR(20),
    remark TEXT,
    signature_url VARCHAR(500),
    created_by UUID REFERENCES staff(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 17. order_items (订单项)
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id),
    item_type VARCHAR(20) NOT NULL,
    item_id UUID,
    item_name VARCHAR(100) NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit_price NUMERIC(12,2) NOT NULL,
    discount NUMERIC(5,2) DEFAULT 100.0,
    amount NUMERIC(12,2) NOT NULL,
    staff_id UUID REFERENCES staff(id),
    card_id UUID REFERENCES member_cards(id),
    times_deducted INTEGER
);

-- 18. payments (支付记录)
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id),
    payment_method_id UUID REFERENCES payment_methods(id),
    payment_method_name VARCHAR(50) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    card_id UUID REFERENCES member_cards(id),
    is_refund BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 19. card_transactions (卡交易流水)
CREATE TABLE IF NOT EXISTS card_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    member_card_id UUID NOT NULL REFERENCES member_cards(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    order_id UUID REFERENCES orders(id),
    transaction_type VARCHAR(20) NOT NULL,
    principal_change NUMERIC(12,2) DEFAULT 0.0,
    present_change NUMERIC(12,2) DEFAULT 0.0,
    times_change INTEGER,
    before_principal NUMERIC(12,2) DEFAULT 0.0,
    after_principal NUMERIC(12,2) DEFAULT 0.0,
    before_present NUMERIC(12,2) DEFAULT 0.0,
    after_present NUMERIC(12,2) DEFAULT 0.0,
    before_times INTEGER,
    after_times INTEGER,
    operator_id UUID REFERENCES staff(id),
    remark TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 20. schedules (排班)
CREATE TABLE IF NOT EXISTS schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    staff_id UUID NOT NULL REFERENCES staff(id),
    shop_id UUID NOT NULL REFERENCES shops(id),
    schedule_date DATE NOT NULL,
    shift_type VARCHAR(20) NOT NULL,
    start_time TIME,
    end_time TIME,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 21. appointments (预约)
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    staff_id UUID NOT NULL REFERENCES staff(id),
    shop_id UUID NOT NULL REFERENCES shops(id),
    room_id UUID REFERENCES rooms(id),
    project_id UUID REFERENCES service_projects(id),
    appointment_date DATE NOT NULL,
    start_time TIME NOT NULL,
    duration INTEGER DEFAULT 60,
    status VARCHAR(20) DEFAULT 'pending',
    remark TEXT,
    created_by UUID REFERENCES staff(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 22. commission_rules (提成规则)
CREATE TABLE IF NOT EXISTS commission_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(20) NOT NULL,
    commission_rate NUMERIC(5,2),
    commission_amount NUMERIC(12,2),
    step_rules JSONB,
    shop_id UUID REFERENCES shops(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 23. commission_records (提成记录)
CREATE TABLE IF NOT EXISTS commission_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    staff_id UUID NOT NULL REFERENCES staff(id),
    order_id UUID REFERENCES orders(id),
    commission_rule_id UUID REFERENCES commission_rules(id),
    commission_type VARCHAR(20) NOT NULL,
    base_amount NUMERIC(12,2) DEFAULT 0.0,
    commission_rate NUMERIC(5,2) DEFAULT 0.0,
    commission_amount NUMERIC(12,2) DEFAULT 0.0,
    month VARCHAR(7) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 24. attendance_rules (考勤规则)
CREATE TABLE IF NOT EXISTS attendance_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shop_id UUID NOT NULL REFERENCES shops(id),
    work_start_time VARCHAR(10) DEFAULT '09:00',
    work_end_time VARCHAR(10) DEFAULT '18:00',
    late_threshold INTEGER DEFAULT 10,
    early_leave_threshold INTEGER DEFAULT 10,
    geofence_enabled BOOLEAN DEFAULT FALSE,
    geofence_latitude NUMERIC(10,7),
    geofence_longitude NUMERIC(10,7),
    geofence_radius INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 25. attendance_records (考勤记录)
CREATE TABLE IF NOT EXISTS attendance_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    staff_id UUID NOT NULL REFERENCES staff(id),
    shop_id UUID NOT NULL REFERENCES shops(id),
    record_date DATE NOT NULL,
    clock_in_time TIMESTAMP,
    clock_out_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'normal',
    clock_in_location VARCHAR(100),
    clock_out_location VARCHAR(100),
    remark VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 26. revisit_tasks (回访任务)
CREATE TABLE IF NOT EXISTS revisit_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    staff_id UUID NOT NULL REFERENCES staff(id),
    shop_id UUID NOT NULL REFERENCES shops(id),
    revisit_type VARCHAR(20) NOT NULL,
    planned_date TIMESTAMP NOT NULL,
    content TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    priority VARCHAR(10) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 27. revisit_records (回访记录)
CREATE TABLE IF NOT EXISTS revisit_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES revisit_tasks(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    staff_id UUID NOT NULL REFERENCES staff(id),
    revisit_method VARCHAR(20) NOT NULL,
    result VARCHAR(20) NOT NULL,
    content TEXT,
    next_plan TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 28. service_logs (服务日志)
CREATE TABLE IF NOT EXISTS service_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    staff_id UUID NOT NULL REFERENCES staff(id),
    shop_id UUID NOT NULL REFERENCES shops(id),
    order_id UUID REFERENCES orders(id),
    project_id UUID REFERENCES service_projects(id),
    service_date TIMESTAMP NOT NULL,
    duration INTEGER,
    before_images TEXT,
    after_images TEXT,
    remark TEXT,
    customer_feedback TEXT,
    status VARCHAR(20) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 29. coupons (优惠券)
CREATE TABLE IF NOT EXISTS coupons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    coupon_type VARCHAR(20) NOT NULL,
    discount_value NUMERIC(12,2) NOT NULL,
    min_amount NUMERIC(12,2) DEFAULT 0.0,
    applicable_type VARCHAR(20) DEFAULT 'all',
    applicable_ids TEXT,
    total_count INTEGER DEFAULT 0,
    used_count INTEGER DEFAULT 0,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    shop_id UUID REFERENCES shops(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 30. marketing_activities (营销活动)
CREATE TABLE IF NOT EXISTS marketing_activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    activity_type VARCHAR(20) NOT NULL,
    description TEXT,
    original_price NUMERIC(12,2),
    activity_price NUMERIC(12,2),
    group_size INTEGER,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_orders INTEGER DEFAULT 0,
    shop_id UUID REFERENCES shops(id),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 31. messages (消息)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shop_id UUID NOT NULL REFERENCES shops(id),
    staff_id UUID REFERENCES staff(id),
    title VARCHAR(200) NOT NULL,
    content TEXT,
    message_type VARCHAR(30) NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    related_id UUID,
    related_type VARCHAR(30),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 32. message_settings (消息设置)
CREATE TABLE IF NOT EXISTS message_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shop_id UUID NOT NULL REFERENCES shops(id),
    card_expire_enabled BOOLEAN DEFAULT TRUE,
    card_expire_days INTEGER DEFAULT 7,
    recharge_enabled BOOLEAN DEFAULT TRUE,
    birthday_enabled BOOLEAN DEFAULT TRUE,
    birthday_days INTEGER DEFAULT 3,
    no_visit_enabled BOOLEAN DEFAULT TRUE,
    no_visit_days INTEGER DEFAULT 30,
    appointment_enabled BOOLEAN DEFAULT TRUE,
    appointment_hours INTEGER DEFAULT 2,
    wechat_notify_enabled BOOLEAN DEFAULT FALSE,
    wechat_app_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 33. skin_tests (皮肤检测)
CREATE TABLE IF NOT EXISTS skin_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    shop_id UUID NOT NULL REFERENCES shops(id),
    device_id VARCHAR(100),
    test_time TIMESTAMP DEFAULT NOW(),
    overall_score INTEGER,
    skin_type VARCHAR(30),
    pore_score INTEGER,
    pore_count INTEGER,
    pore_diameter NUMERIC(6,2),
    acne_score INTEGER,
    acne_count INTEGER,
    spot_score INTEGER,
    spot_area NUMERIC(6,2),
    wrinkle_score INTEGER,
    wrinkle_count INTEGER,
    skin_color_score INTEGER,
    skin_brightness INTEGER,
    moisture_score INTEGER,
    moisture_index INTEGER,
    sensitive_score INTEGER,
    sensitive_level VARCHAR(20),
    blackhead_score INTEGER,
    blackhead_count INTEGER,
    front_image VARCHAR(500),
    left_image VARCHAR(500),
    right_image VARCHAR(500),
    remark TEXT,
    report_url VARCHAR(500),
    operator_id UUID REFERENCES staff(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_rooms_shop_id ON rooms(shop_id);
CREATE INDEX IF NOT EXISTS idx_staff_shop_id ON staff(shop_id);
CREATE INDEX IF NOT EXISTS idx_staff_phone ON staff(phone);
CREATE INDEX IF NOT EXISTS idx_customers_shop_id ON customers(shop_id);
CREATE INDEX IF NOT EXISTS idx_customers_code ON customers(code);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customer_tags_customer ON customer_tags(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_tags_tag ON customer_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_service_projects_category ON service_projects(category_id);
CREATE INDEX IF NOT EXISTS idx_member_cards_customer ON member_cards(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_shop ON orders(shop_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_card_transactions_card ON card_transactions(member_card_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_schedules_staff_date ON schedules(staff_id, schedule_date);
CREATE INDEX IF NOT EXISTS idx_attendance_staff_date ON attendance_records(staff_id, record_date);
CREATE INDEX IF NOT EXISTS idx_commission_records_staff ON commission_records(staff_id, month);
CREATE INDEX IF NOT EXISTS idx_messages_shop ON messages(shop_id, is_read);

-- ============================================
-- SEED DATA
-- ============================================

-- Fixed UUIDs for referential integrity
-- Shop
INSERT INTO shops (id, name, code, address, phone, is_active)
VALUES ('a0000000-0000-0000-0000-000000000001', '余几美雕科技皮肤管理', 'SHOP001', '上海市浦东新区世纪大道100号', '021-12345678', TRUE);

-- Rooms
INSERT INTO rooms (id, shop_id, name, beds, floor, is_active) VALUES
('b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'VIP室1', 1, 1, TRUE),
('b0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'VIP室2', 1, 1, TRUE),
('b0000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001', '普通室1', 2, 2, TRUE),
('b0000000-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000001', '普通室2', 2, 2, TRUE);

-- Positions
INSERT INTO positions (id, name, sort_order) VALUES
('c0000000-0000-0000-0000-000000000001', '店长', 1),
('c0000000-0000-0000-0000-000000000002', '美容师', 2),
('c0000000-0000-0000-0000-000000000003', '技师', 3),
('c0000000-0000-0000-0000-000000000004', '前台', 4),
('c0000000-0000-0000-0000-000000000005', '收银员', 5);

-- Staff (password: 123456 - bcrypt hash)
INSERT INTO staff (id, name, phone, password_hash, shop_id, position_id, role, is_active, hire_date) VALUES
('d0000000-0000-0000-0000-000000000001', '店长', '13800138000',
 '$2b$12$TVlrxrA8xB9W.rBq6Yv3I.APquc6aRUe3PDI2BLm7GSHrS9el1FUG',
 'a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', 'admin', TRUE, '2023-01-01'),
('d0000000-0000-0000-0000-000000000002', '李美容师', '13800138001',
 '$2b$12$TVlrxrA8xB9W.rBq6Yv3I.APquc6aRUe3PDI2BLm7GSHrS9el1FUG',
 'a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000002', 'staff', TRUE, '2023-03-01'),
('d0000000-0000-0000-0000-000000000003', '王技师', '13800138002',
 '$2b$12$TVlrxrA8xB9W.rBq6Yv3I.APquc6aRUe3PDI2BLm7GSHrS9el1FUG',
 'a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000003', 'staff', TRUE, '2023-06-01'),
('d0000000-0000-0000-0000-000000000004', '陈前台', '13800138003',
 '$2b$12$TVlrxrA8xB9W.rBq6Yv3I.APquc6aRUe3PDI2BLm7GSHrS9el1FUG',
 'a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000004', 'staff', TRUE, '2024-01-01');

-- Tags
INSERT INTO tags (id, name, color, shop_id) VALUES
('e0000000-0000-0000-0000-000000000001', 'VIP', '#FF6B8A', 'a0000000-0000-0000-0000-000000000001'),
('e0000000-0000-0000-0000-000000000002', '新客', '#4CAF50', 'a0000000-0000-0000-0000-000000000001'),
('e0000000-0000-0000-0000-000000000003', '高消费', '#FF9800', 'a0000000-0000-0000-0000-000000000001'),
('e0000000-0000-0000-0000-000000000004', '敏感肌', '#9C27B0', 'a0000000-0000-0000-0000-000000000001'),
('e0000000-0000-0000-0000-000000000005', '需回访', '#2196F3', 'a0000000-0000-0000-0000-000000000001');

-- Sources
INSERT INTO sources (id, name, shop_id) VALUES
('e1000000-0000-0000-0000-000000000001', '自然到店', 'a0000000-0000-0000-0000-000000000001'),
('e1000000-0000-0000-0000-000000000002', '朋友推荐', 'a0000000-0000-0000-0000-000000000001'),
('e1000000-0000-0000-0000-000000000003', '美团', 'a0000000-0000-0000-0000-000000000001'),
('e1000000-0000-0000-0000-000000000004', '抖音', 'a0000000-0000-0000-0000-000000000001'),
('e1000000-0000-0000-0000-000000000005', '大众点评', 'a0000000-0000-0000-0000-000000000001'),
('e1000000-0000-0000-0000-000000000006', '微信公众号', 'a0000000-0000-0000-0000-000000000001');

-- Customers
INSERT INTO customers (id, name, code, phone, gender, birthday, shop_id, source_id, staff_id, level, balance, points, total_consumption, last_visit_at, remark, taboo) VALUES
('f0000000-0000-0000-0000-000000000001', '张美丽', 'C0001', '13812341234', 'female', '1990-05-20',
 'a0000000-0000-0000-0000-000000000001', 'e1000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000002',
 'gold', 3580.00, 2580, 12800.00, '2024-10-08', '喜欢深层清洁项目', NULL),
('f0000000-0000-0000-0000-000000000002', '王芳芳', 'C0002', '13956785678', 'female', '1988-11-15',
 'a0000000-0000-0000-0000-000000000001', 'e1000000-0000-0000-0000-000000000002', 'd0000000-0000-0000-0000-000000000003',
 'silver', 1200.00, 1200, 5600.00, '2024-10-07', NULL, NULL),
('f0000000-0000-0000-0000-000000000003', '李雅婷', 'C0003', '13790129012', 'female', '1992-03-08',
 'a0000000-0000-0000-0000-000000000001', 'e1000000-0000-0000-0000-000000000003', 'd0000000-0000-0000-0000-000000000002',
 'platinum', 5000.00, 4500, 25000.00, '2024-10-06', NULL, '对酒精过敏'),
('f0000000-0000-0000-0000-000000000004', '陈雪梅', 'C0004', '13634563456', 'female', '1985-07-22',
 'a0000000-0000-0000-0000-000000000001', 'e1000000-0000-0000-0000-000000000004', NULL,
 'normal', 0.00, 500, 3000.00, '2024-09-30', NULL, NULL),
('f0000000-0000-0000-0000-000000000005', '刘晓燕', 'C0005', '13578907890', 'female', '1995-12-25',
 'a0000000-0000-0000-0000-000000000001', 'e1000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000002',
 'diamond', 8000.00, 8000, 35000.00, '2024-10-09', '每月固定来做面部护理', NULL);

-- Categories
INSERT INTO categories (id, name, category_type, shop_id, sort_order) VALUES
('e2000000-0000-0000-0000-000000000001', '面部护理', 'project', 'a0000000-0000-0000-0000-000000000001', 1),
('e2000000-0000-0000-0000-000000000002', '身体护理', 'project', 'a0000000-0000-0000-0000-000000000001', 2),
('e2000000-0000-0000-0000-000000000003', '美甲美睫', 'project', 'a0000000-0000-0000-0000-000000000001', 3);

-- Service Projects
INSERT INTO service_projects (id, name, category_id, price, member_price, duration, shop_id, commission_rate) VALUES
('e3000000-0000-0000-0000-000000000001', '深层清洁', 'e2000000-0000-0000-0000-000000000001', 298.00, 258.00, 60, 'a0000000-0000-0000-0000-000000000001', 10.00),
('e3000000-0000-0000-0000-000000000002', '面部护理', 'e2000000-0000-0000-0000-000000000001', 398.00, 348.00, 90, 'a0000000-0000-0000-0000-000000000001', 12.00),
('e3000000-0000-0000-0000-000000000003', '补水保湿', 'e2000000-0000-0000-0000-000000000001', 268.00, 228.00, 45, 'a0000000-0000-0000-0000-000000000001', 10.00),
('e3000000-0000-0000-0000-000000000004', '全身SPA', 'e2000000-0000-0000-0000-000000000002', 998.00, 888.00, 120, 'a0000000-0000-0000-0000-000000000001', 15.00),
('e3000000-0000-0000-0000-000000000005', '精油推拿', 'e2000000-0000-0000-0000-000000000002', 598.00, 498.00, 90, 'a0000000-0000-0000-0000-000000000001', 12.00),
('e3000000-0000-0000-0000-000000000006', '美甲', 'e2000000-0000-0000-0000-000000000003', 198.00, 168.00, 60, 'a0000000-0000-0000-0000-000000000001', 8.00),
('e3000000-0000-0000-0000-000000000007', '美睫', 'e2000000-0000-0000-0000-000000000003', 298.00, 258.00, 45, 'a0000000-0000-0000-0000-000000000001', 10.00);

-- Payment Methods
INSERT INTO payment_methods (id, name, sort_order, shop_id) VALUES
('e4000000-0000-0000-0000-000000000001', '现金', 1, 'a0000000-0000-0000-0000-000000000001'),
('e4000000-0000-0000-0000-000000000002', '微信支付', 2, 'a0000000-0000-0000-0000-000000000001'),
('e4000000-0000-0000-0000-000000000003', '支付宝', 3, 'a0000000-0000-0000-0000-000000000001'),
('e4000000-0000-0000-0000-000000000004', '刷卡', 4, 'a0000000-0000-0000-0000-000000000001'),
('e4000000-0000-0000-0000-000000000005', '储值卡', 5, 'a0000000-0000-0000-0000-000000000001'),
('e4000000-0000-0000-0000-000000000006', '次卡抵扣', 6, 'a0000000-0000-0000-0000-000000000001');

-- Card Types
INSERT INTO card_types (id, name, card_category, sell_price, face_value, present_amount, validity_type, validity_days, shop_id, description) VALUES
('e5000000-0000-0000-0000-000000000001', '银卡储值', 'stored_value', 1000.00, 1000.00, 100.00, 'permanent', NULL, 'a0000000-0000-0000-0000-000000000001', '充值1000送100'),
('e5000000-0000-0000-0000-000000000002', '金卡储值', 'stored_value', 3000.00, 3000.00, 500.00, 'permanent', NULL, 'a0000000-0000-0000-0000-000000000001', '充值3000送500'),
('e5000000-0000-0000-0000-000000000003', '面部护理10次卡', 'times', 3000.00, 3980.00, 0.00, 'days', 365, 'a0000000-0000-0000-0000-000000000001', '面部护理10次，有效期1年');

-- Attendance Rule
INSERT INTO attendance_rules (id, shop_id, work_start_time, work_end_time, late_threshold, early_leave_threshold)
VALUES (uuid_generate_v4(), 'a0000000-0000-0000-0000-000000000001', '09:00', '18:00', 10, 10);

-- Message Settings
INSERT INTO message_settings (id, shop_id)
VALUES (uuid_generate_v4(), 'a0000000-0000-0000-0000-000000000001');

COMMIT;

-- ============================================
-- SUMMARY
-- ============================================
-- Tables created: 33
-- Shop: 余几美雕科技皮肤管理
-- Rooms: 4 (VIP室1, VIP室2, 普通室1, 普通室2)
-- Positions: 5 (店长, 美容师, 技师, 前台, 收银员)
-- Staff: 4 (admin: 13800138000 / 123456)
-- Tags: 5 (VIP, 新客, 高消费, 敏感肌, 需回访)
-- Sources: 6 (自然到店, 朋友推荐, 美团, 抖音, 大众点评, 微信公众号)
-- Customers: 5
-- Categories: 3 (面部护理, 身体护理, 美甲美睫)
-- Service Projects: 7
-- Payment Methods: 6
-- Card Types: 3 (银卡储值, 金卡储值, 面部护理10次卡)
-- ============================================
