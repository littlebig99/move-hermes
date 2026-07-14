"""Move Hermes — 数据库初始化 + 迁移"""
import sys
from pathlib import Path
from typing import Optional

# 兼容直接运行和包导入
try:
    from .connection import get_connection
except ImportError:
    _backend = str(Path(__file__).resolve().parent)
    if _backend not in sys.path:
        sys.path.insert(0, _backend)
    from connection import get_connection


def init_db(db_path: Optional[str] = None):
    """初始化数据库，创建所有表"""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
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
                delivery_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER REFERENCES orders(id),
                task_name TEXT NOT NULL,
                sequence_num INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                worker_id INTEGER,
                worker_name TEXT,
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL DEFAULT 'openai',
                api_key TEXT NOT NULL DEFAULT '',
                model TEXT DEFAULT 'gpt-4o-mini',
                base_url TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wecom_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                corp_id TEXT DEFAULT '',
                agent_id TEXT DEFAULT '',
                secret TEXT DEFAULT '',
                webhook_url TEXT DEFAULT '',
                is_active INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feishu_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT DEFAULT '',
                app_secret TEXT DEFAULT '',
                verify_token TEXT DEFAULT '',
                is_active INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    path = _resolve_db_path(db_path)
    print(f"[OK] 数据库初始化完成: {path}")
    
    # 数据库迁移：为已有数据库添加新字段
    _migrate_db(db_path)


def _migrate_db(db_path: Optional[str] = None):
    """迁移已有数据库表结构"""
    with get_connection(db_path) as conn:
        cursor = conn.execute("PRAGMA table_info(feishu_config)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "verify_token" not in columns:
            conn.execute("ALTER TABLE feishu_config ADD COLUMN verify_token TEXT DEFAULT ''")
            print("  → 已为 feishu_config 添加 verify_token 列")


def _resolve_db_path(db_path=None):
    """临时引用 — 实际应从 connection 导入"""
    try:
        from .connection import _resolve_db_path as rp
    except ImportError:
        from connection import _resolve_db_path as rp
    return rp(db_path)


def get_overdue_orders(db_path=None):
    """获取逾期订单（交货日期已过但未完成）"""
    import datetime
    try:
        from .connection import get_connection
    except ImportError:
        from connection import get_connection
    today = datetime.date.today().isoformat()
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT o.*, c.name as customer_name, p.name as product_name
               FROM orders o
               LEFT JOIN customers c ON o.customer_id = c.id
               LEFT JOIN products p ON o.product_id = p.id
               WHERE o.delivery_date < ?
                 AND o.status NOT IN ('completed', 'shipped')
               ORDER BY o.delivery_date ASC""",
            (today,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_upcoming_delivery(days=3, db_path=None):
    """获取即将到期的订单（未来N天内交货）"""
    import datetime
    try:
        from .connection import get_connection
    except ImportError:
        from connection import get_connection
    soon = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
    today = datetime.date.today().isoformat()
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT o.*, c.name as customer_name, p.name as product_name
               FROM orders o
               LEFT JOIN customers c ON o.customer_id = c.id
               LEFT JOIN products p ON o.product_id = p.id
               WHERE o.delivery_date BETWEEN ? AND ?
                 AND o.status NOT IN ('completed', 'shipped')
               ORDER BY o.delivery_date ASC""",
            (today, soon)
        ).fetchall()
        return [dict(r) for r in rows]
