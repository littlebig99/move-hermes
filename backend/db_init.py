"""
Move Hermes — 数据库初始化模块
"""
import sqlite3
from pathlib import Path

DB_PATH = None

def init_db(db_path: str = None):
    """初始化数据库，创建所有表"""
    global DB_PATH
    if db_path is None:
        db_path = str(Path(__file__).parent.parent / "data" / "move_hermes.db")
    DB_PATH = db_path
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    cursor = conn.cursor()
    
    # 客户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT,
            phone TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 产品表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            spec TEXT,
            unit TEXT DEFAULT '件',
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 订单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
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
        )
    """)
    
    # 订单工序表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_tasks (
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
        )
    """)
    
    # 生产日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS production_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER REFERENCES order_tasks(id),
            photo_url TEXT,
            ai_extracted TEXT,
            status TEXT DEFAULT 'pending_review',
            worker_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # API配置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            api_key TEXT NOT NULL,
            model TEXT DEFAULT 'gpt-4o-mini',
            base_url TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 企业微信配置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wecom_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corp_id TEXT,
            agent_id TEXT,
            secret TEXT,
            webhook_url TEXT,
            is_active INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 飞书配置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feishu_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_id TEXT,
            app_secret TEXT,
            is_active INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"[OK] 数据库初始化完成: {db_path}")
