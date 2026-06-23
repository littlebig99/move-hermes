## 4. 数据库设计

### 4.1 ER图

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   customer   │     │      order       │     │  product     │
├──────────────┤     ├──────────────────┤     ├──────────────┤
│ id (PK)      │──┐  │ id (PK)          │  ┌──│ id (PK)      │
│ name         │  │  │ customer_id (FK) │  │  │ name         │
│ contact      │  │  │ product_id (FK)  │  │  │ spec         │
│ phone        │  │  │ quantity         │  │  │ unit         │
│ created_at   │  │  │ unit_price       │  │  │ category     │
└──────────────┘  │  │ total_amount     │  │  │ created_at   │
                  │  │ status           │  └──────────────┘
                  │  │ priority (normal │
                  │  │   urgent)        │
                  │  │ notes            │
                  │  │ created_at       │
                  │  │ updated_at       │
                  │  └────────┬─────────┘
                  │           │
                  │     ┌─────▼──────────┐
                  │     │   order_task   │
                  │     ├────────────────┤
                  │     │ id (PK)        │
                  │     │ order_id (FK)  │
                  │     │ task_name      │
                  │     │ sequence_num   │
                  │     │ status         │
                  │     │ worker_id      │
                  │     │ started_at     │
                  │     │ completed_at   │
                  │     │ photo_url      │
                  │     │ ai_confidence  │
                  │     │ notes          │
                  │     └────────────────┘
                  │
            ┌─────▼──────────┐
            │   production_log │
            ├────────────────┤
            │ id (PK)        │
            │ task_id (FK)   │
            │ photo_url      │
            │ ai_extracted   │
            │ status         │
            │ worker_name    │
            │ created_at     │
            └────────────────┘
```

### 4.2 表结构详情

#### customers（客户表）
```sql
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact TEXT,
    phone TEXT,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### products（产品表）
```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    spec TEXT,
    unit TEXT DEFAULT '件',
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### orders（订单表）
```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    product_id INTEGER REFERENCES products(id),
    quantity REAL NOT NULL,
    unit_price REAL,
    total_amount REAL,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'normal',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### order_tasks（订单工序表）
```sql
CREATE TABLE order_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER REFERENCES orders(id),
    task_name TEXT NOT NULL,
    sequence_num INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    worker_id INTEGER,
    assigned_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    photo_url TEXT,
    ai_confidence REAL,
    ai_notes TEXT,
    is_stalled INTEGER DEFAULT 0,
    stalled_since TIMESTAMP
);
```

#### production_logs（生产日志表）
```sql
CREATE TABLE production_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES order_tasks(id),
    photo_url TEXT,
    ai_extracted TEXT,
    status TEXT DEFAULT 'pending_review',
    worker_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### api_config（API配置表）
```sql
CREATE TABLE api_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    api_key TEXT NOT NULL,
    model TEXT DEFAULT 'gpt-4o-mini',
    base_url TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### wecom_config（企业微信配置表）
```sql
CREATE TABLE wecom_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    corp_id TEXT,
    agent_id TEXT,
    secret TEXT,
    webhook_url TEXT,
    is_active INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### feishu_config（飞书配置表）
```sql
CREATE TABLE feishu_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id TEXT,
    app_secret TEXT,
    is_active INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
