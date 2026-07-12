"""
Move Hermes — 数据库管理器
统一管理SQLite连接和事务
"""
import sqlite3
import os
import threading
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple
import datetime

# ==================== 线程安全的数据库路径管理 ====================
_db_path_lock = threading.Lock()
_DB_PATH: Optional[str] = None


def get_db_path() -> str:
    """获取当前数据库路径（线程安全）"""
    global _DB_PATH
    with _db_path_lock:
        return _DB_PATH or ""


def set_db_path(path: str):
    """设置数据库路径（线程安全）"""
    global _DB_PATH
    with _db_path_lock:
        _DB_PATH = path


def _resolve_db_path(db_path: Optional[str] = None) -> str:
    """解析数据库路径"""
    global _DB_PATH
    with _db_path_lock:
        if db_path is not None:
            _DB_PATH = db_path
        elif _DB_PATH is None:
            script_dir = Path(__file__).parent.parent
            data_dir = script_dir / "data"
            data_dir.mkdir(exist_ok=True)
            _DB_PATH = str(data_dir / "move_hermes.db")
        return _DB_PATH


@contextmanager
def get_connection(db_path: Optional[str] = None):
    """获取数据库连接的上下文管理器"""
    path = _resolve_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()


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
        # AI 配置
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
        # 企业微信配置
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
        # 飞书配置
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
    print(f"✅ 数据库初始化完成: {path}")
    
    # 数据库迁移：为已有数据库添加新字段
    _migrate_db(db_path)


def _migrate_db(db_path: Optional[str] = None):
    """迁移已有数据库表结构"""
    with get_connection(db_path) as conn:
        # 检查 feishu_config 是否有 verify_token
        cursor = conn.execute("PRAGMA table_info(feishu_config)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "verify_token" not in columns:
            conn.execute("ALTER TABLE feishu_config ADD COLUMN verify_token TEXT DEFAULT ''")
            print("  → 已为 feishu_config 添加 verify_token 列")
        
        # 检查 wecom_config 是否有默认值约束（不影响功能，仅提示）




# ==================== 订单操作 ====================

def generate_order_no(db_path: Optional[str] = None) -> str:
    """生成订单编号: ORD-YYYYMMDD-NNN"""
    today = datetime.date.today().strftime("%Y%m%d")
    prefix = f"ORD-{today}-"
    
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT MAX(order_no) FROM orders WHERE order_no LIKE ?",
            (prefix + "%",)
        ).fetchone()
        
        if row[0]:
            last_num = int(row[0].split("-")[-1])
            next_num = last_num + 1
        else:
            next_num = 1
        
        return f"{prefix}{next_num:03d}"


def create_order(
    customer_id: int,
    product_id: int,
    quantity: float,
    unit_price: Optional[float] = None,
    priority: str = "normal",
    notes: Optional[str] = None,
    delivery_date: Optional[str] = None,
    order_no: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """创建订单"""
    with get_connection(db_path) as conn:
        if not order_no:
            order_no = generate_order_no(db_path)
        
        total_amount = quantity * (unit_price or 0)
        
        cursor = conn.execute(
            """INSERT INTO orders 
               (order_no, customer_id, product_id, quantity, unit_price, 
                total_amount, status, priority, notes, delivery_date)
               VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
            (order_no, customer_id, product_id, quantity, unit_price,
             total_amount, priority, notes, delivery_date)
        )
        order_id = cursor.lastrowid
        
        # 创建默认工序
        default_tasks = ["下料", "加工", "组装", "质检", "包装", "发货"]
        for i, task_name in enumerate(default_tasks, 1):
            conn.execute(
                "INSERT INTO order_tasks (order_id, task_name, sequence_num, status) VALUES (?, ?, ?, 'pending')",
                (order_id, task_name, i)
            )
        
        order = conn.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        
        return _row_to_dict(order)


# ==================== SQL 安全白名单 ====================
_ALLOWED_ORDER_COLUMNS = {"status", "priority", "customer_id"}


def _build_safe_where(allowed_columns: set, conditions: list, params: list) -> str:
    """构建安全的 WHERE 子句 — 只允许白名单中的列名
    
    Args:
        allowed_columns: 允许的列名集合（用于防止 SQL 注入）
        conditions: 条件列表，每项为 "(column = ?)" 格式
        params: 参数列表
    
    Returns:
        完整的 WHERE 子句字符串
    """
    # 验证所有条件都使用白名单列名
    for cond in conditions:
        # 提取列名（从 "column = ?" 格式）
        col_name = cond.split("=")[0].strip().split(".")[-1].strip()
        if col_name not in allowed_columns:
            raise ValueError(f"不允许的查询列: {col_name}")
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    return where_clause


def list_orders(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """获取订单列表"""
    conditions = []
    params = []
    
    if status:
        conditions.append("o.status = ?")
        params.append(status)
    if priority:
        conditions.append("o.priority = ?")
        params.append(priority)
    if customer_id:
        conditions.append("o.customer_id = ?")
        params.append(customer_id)
    if search:
        conditions.append("(o.order_no LIKE ? OR o.notes LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    
    where_clause = _build_safe_where(_ALLOWED_ORDER_COLUMNS, conditions, params)
    
    with get_connection(db_path) as conn:
        # 总数
        count_row = conn.execute(
            f"SELECT COUNT(*) FROM orders o {where_clause}", params
        ).fetchone()
        total = count_row[0]
        
        # 分页查询
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"""SELECT o.*, c.name as customer_name, p.name as product_name
                FROM orders o
                LEFT JOIN customers c ON o.customer_id = c.id
                LEFT JOIN products p ON o.product_id = p.id
                {where_clause}
                ORDER BY CASE WHEN o.priority = 'urgent' THEN 0 ELSE 1 END,
                         o.created_at DESC
                LIMIT ? OFFSET ?""",
            params + [page_size, offset]
        ).fetchall()
        
        return {
            "orders": [_row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }


def get_order(order_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """获取订单详情（含工序）"""
    with get_connection(db_path) as conn:
        order = conn.execute(
            """SELECT o.*, c.name as customer_name, c.phone as customer_phone,
                      p.name as product_name, p.spec as product_spec
               FROM orders o
               LEFT JOIN customers c ON o.customer_id = c.id
               LEFT JOIN products p ON o.product_id = p.id
               WHERE o.id = ?""",
            (order_id,)
        ).fetchone()
        
        if not order:
            return None
        
        tasks = conn.execute(
            "SELECT * FROM order_tasks WHERE order_id = ? ORDER BY sequence_num",
            (order_id,)
        ).fetchall()
        
        result = _row_to_dict(order)
        result["tasks"] = [_row_to_dict(t) for t in tasks]
        return result


def update_order(
    order_id: int,
    updates: Dict[str, Any],
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """更新订单"""
    allowed_fields = {"status", "priority", "notes", "delivery_date"}
    set_clauses = []
    params = []
    
    for key, value in updates.items():
        if key in allowed_fields and value is not None:
            set_clauses.append(f"{key} = ?")
            params.append(value)
    
    if not set_clauses:
        return None
    
    params.append(order_id)
    
    with get_connection(db_path) as conn:
        conn.execute(
            f"UPDATE orders SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            params
        )
        
        row = conn.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        if not row:
            return None
        result = _row_to_dict(row)
        # 关联信息
        cust_row = conn.execute(
            "SELECT name FROM customers WHERE id = ?", (result.get("customer_id"),)
        ).fetchone()
        result["customer_name"] = cust_row[0] if cust_row else None
        prod_row = conn.execute(
            "SELECT name FROM products WHERE id = ?", (result.get("product_id"),)
        ).fetchone()
        result["product_name"] = prod_row[0] if prod_row else None
        # 关联工序
        result["tasks"] = [
            _row_to_dict(t) for t in conn.execute(
                "SELECT * FROM order_tasks WHERE order_id = ? ORDER BY sequence_num",
                (order_id,)
            ).fetchall()
        ]
        return result


def delete_order(order_id: int, db_path: Optional[str] = None) -> bool:
    """删除订单"""
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        return cursor.rowcount > 0


def mark_urgent(order_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """标记加急"""
    return update_order(order_id, {"priority": "urgent"}, db_path)


# ==================== 工序操作 ====================

def get_order_tasks(order_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取订单的所有工序"""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM order_tasks WHERE order_id = ? ORDER BY sequence_num",
            (order_id,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def add_task(
    order_id: int,
    task_name: str,
    sequence_num: int,
    worker_id: Optional[int] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """添加新工序"""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO order_tasks (order_id, task_name, sequence_num, status) VALUES (?, ?, ?, 'pending')",
            (order_id, task_name, sequence_num)
        )
        task = conn.execute(
            "SELECT * FROM order_tasks WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_dict(task)


def update_task_status(
    task_id: int,
    status: str,
    worker_id: Optional[int] = None,
    worker_name: Optional[str] = None,
    photo_url: Optional[str] = None,
    ai_confidence: Optional[float] = None,
    ai_notes: Optional[str] = None,
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """更新工序状态"""
    now = datetime.datetime.now().isoformat()
    
    set_clauses = ["status = ?"]
    params = [status]
    
    if status == "in_progress":
        set_clauses.append("started_at = ?")
        params.append(now)
    elif status == "completed":
        set_clauses.append("completed_at = ?")
        params.append(now)
    
    if worker_id is not None:
        set_clauses.append("worker_id = ?")
        params.append(worker_id)
    if worker_name is not None:
        set_clauses.append("worker_name = ?")
        params.append(worker_name)
    if photo_url is not None:
        set_clauses.append("photo_url = ?")
        params.append(photo_url)
    if ai_confidence is not None:
        set_clauses.append("ai_confidence = ?")
        params.append(ai_confidence)
    if ai_notes is not None:
        set_clauses.append("ai_notes = ?")
        params.append(ai_notes)
    
    params.append(task_id)
    
    with get_connection(db_path) as conn:
        conn.execute(
            f"UPDATE order_tasks SET {', '.join(set_clauses)} WHERE id = ?",
            params
        )
        
        task = conn.execute(
            "SELECT * FROM order_tasks WHERE id = ?", (task_id,)
        ).fetchone()
        
        if task:
            result = _row_to_dict(task)
            # 如果完成，检查是否有下一道工序
            next_task = conn.execute(
                "SELECT * FROM order_tasks WHERE order_id = ? AND sequence_num = ? AND status = 'pending'",
                (result["order_id"], result["sequence_num"] + 1)
            ).fetchone()
            result["next_task"] = _row_to_dict(next_task) if next_task else None
            return result
        
        return None


def delete_task(task_id: int, db_path: Optional[str] = None) -> bool:
    """删除工序"""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT id FROM order_tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM order_tasks WHERE id = ?", (task_id,))
        return True


def get_stalled_tasks(threshold_days: int = 2, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取呆滞工序"""
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=threshold_days)).isoformat()
    
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT ot.*, o.order_no, o.priority, c.name as customer_name
               FROM order_tasks ot
               JOIN orders o ON ot.order_id = o.id
               LEFT JOIN customers c ON o.customer_id = c.id
               WHERE ot.status IN ('pending', 'in_progress')
                 AND ot.started_at < ?
               ORDER BY CASE WHEN o.priority = 'urgent' THEN 0 ELSE 1 END,
                        ot.started_at ASC""",
            (cutoff,)
        ).fetchall()
        
        result = []
        for row in rows:
            d = _row_to_dict(row)
            if d.get("started_at"):
                started = datetime.datetime.fromisoformat(d["started_at"])
                d["stalled_days"] = (datetime.datetime.now() - started).days
            else:
                d["stalled_days"] = threshold_days  # 从未开始的也算
            result.append(d)
        
        return result


# ==================== 看板统计 ====================

def get_dashboard_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """获取看板统计数据"""
    with get_connection(db_path) as conn:
        # 按状态统计
        status_counts = {}
        for row in conn.execute(
            "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status"
        ).fetchall():
            status_counts[row["status"]] = row["cnt"]
        
        # 加急订单
        urgent = conn.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE priority = 'urgent'"
        ).fetchone()["cnt"]
        
        # 呆滞工序
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat()
        stalled_count = conn.execute(
            "SELECT COUNT(*) FROM order_tasks WHERE status IN ('pending', 'in_progress') AND started_at < ?",
            (cutoff,)
        ).fetchone()[0]
        
        # 今日新增
        today = datetime.date.today().isoformat()
        today_new = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE DATE(created_at) = ?",
            (today,)
        ).fetchone()[0]
        
        return {
            "in_production": status_counts.get("producing", 0),
            "pending": status_counts.get("pending", 0),
            "completed": status_counts.get("completed", 0),
            "shipped": status_counts.get("shipped", 0),
            "urgent": urgent,
            "stalled": stalled_count,
            "today_new": today_new
        }


def get_dashboard_production(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取生产进度看板数据"""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT o.id, o.order_no, o.priority, o.status,
                      c.name as customer_name, p.name as product_name,
                      o.quantity, o.delivery_date
               FROM orders o
               LEFT JOIN customers c ON o.customer_id = c.id
               LEFT JOIN products p ON o.product_id = p.id
               WHERE o.status != 'completed' AND o.status != 'shipped'
               ORDER BY CASE WHEN o.priority = 'urgent' THEN 0 ELSE 1 END,
                        o.delivery_date ASC"""
        ).fetchall()
        
        result = []
        for row in rows:
            order = _row_to_dict(row)
            tasks = conn.execute(
                "SELECT id, task_name, status, sequence_num FROM order_tasks WHERE order_id = ? ORDER BY sequence_num",
                (order["id"],)
            ).fetchall()
            order["tasks"] = [
                {"id": t["id"], "name": t["task_name"], "status": t["status"], "seq": t["sequence_num"]}
                for t in tasks
            ]
            result.append(order)
        
        return result


# ==================== 客户操作 ====================

def list_customers(page: int = 1, page_size: int = 20, db_path: Optional[str] = None) -> Dict[str, Any]:
    """获取客户列表"""
    offset = (page - 1) * page_size
    with get_connection(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM customers ORDER BY name LIMIT ? OFFSET ?",
            (page_size, offset)
        ).fetchall()
        return {
            "customers": [_row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size
        }


def create_customer(name: str, contact: Optional[str] = None, phone: Optional[str] = None,
                    address: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """创建客户"""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO customers (name, contact, phone, address) VALUES (?, ?, ?, ?)",
            (name, contact, phone, address)
        )
        customer = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_dict(customer)


def update_customer(customer_id: int, updates: Dict[str, Any], db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """更新客户"""
    allowed = {"name", "contact", "phone", "address"}
    set_clauses = []
    params = []
    for k, v in updates.items():
        if k in allowed and v is not None:
            set_clauses.append(f"{k} = ?")
            params.append(v)
    if not set_clauses:
        return None
    params.append(customer_id)
    with get_connection(db_path) as conn:
        conn.execute(
            f"UPDATE customers SET {', '.join(set_clauses)} WHERE id = ?", params
        )
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if not row:
            return None
        result = _row_to_dict(row)
        result["order_count"] = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE customer_id = ?", (customer_id,)
        ).fetchone()[0]
        return result


def get_customer(customer_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """获取客户详情"""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if not row:
            return None
        result = _row_to_dict(row)
        # 关联订单数
        result["order_count"] = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE customer_id = ?", (customer_id,)
        ).fetchone()[0]
        return result


def delete_customer(customer_id: int, db_path: Optional[str] = None) -> bool:
    """删除客户"""
    with get_connection(db_path) as conn:
        return conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,)).rowcount > 0


# ==================== 产品操作 ====================

def list_products(page: int = 1, page_size: int = 20, db_path: Optional[str] = None) -> Dict[str, Any]:
    """获取产品列表"""
    offset = (page - 1) * page_size
    with get_connection(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM products ORDER BY name LIMIT ? OFFSET ?",
            (page_size, offset)
        ).fetchall()
        return {
            "products": [_row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size
        }


def create_product(name: str, spec: Optional[str] = None, unit: str = "件",
                   category: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """创建产品"""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO products (name, spec, unit, category) VALUES (?, ?, ?, ?)",
            (name, spec, unit, category)
        )
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_dict(product)


def update_product(product_id: int, updates: Dict[str, Any], db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """更新产品"""
    allowed = {"name", "spec", "unit", "category"}
    set_clauses = []
    params = []
    for k, v in updates.items():
        if k in allowed and v is not None:
            set_clauses.append(f"{k} = ?")
            params.append(v)
    if not set_clauses:
        return None
    params.append(product_id)
    with get_connection(db_path) as conn:
        conn.execute(
            f"UPDATE products SET {', '.join(set_clauses)} WHERE id = ?", params
        )
        return get_product(product_id, db_path)


def get_product(product_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """获取产品详情"""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not row:
            return None
        result = _row_to_dict(row)
        result["order_count"] = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE product_id = ?", (product_id,)
        ).fetchone()[0]
        return result


def delete_product(product_id: int, db_path: Optional[str] = None) -> bool:
    """删除产品"""
    with get_connection(db_path) as conn:
        return conn.execute("DELETE FROM products WHERE id = ?", (product_id,)).rowcount > 0


# ==================== 配置管理操作 ====================

def get_api_config(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """获取AI API配置"""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM api_config WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        if not row:
            return None
        result = _row_to_dict(row)
        result["api_key"] = "***"
        return result


def save_api_config(provider: str, api_key: str, model: str = "gpt-4o-mini",
                    base_url: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """保存AI API配置"""
    with get_connection(db_path) as conn:
        conn.execute("UPDATE api_config SET is_active = 0")
        cursor = conn.execute(
            "INSERT INTO api_config (provider, api_key, model, base_url, is_active) VALUES (?, ?, ?, ?, 1)",
            (provider, api_key, model, base_url)
        )
        config = conn.execute(
            "SELECT * FROM api_config WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        result = _row_to_dict(config)
        result["api_key"] = "***"
        return result


def get_wecom_config(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """获取企业微信配置"""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM wecom_config WHERE id = 1"
        ).fetchone()
        if not row:
            return {"corp_id": "", "agent_id": "", "secret": "", "webhook_url": "", "is_active": 0}
        return _row_to_dict(row)


def save_wecom_config(corp_id: str, agent_id: str, secret: str,
                      webhook_url: str, is_active: int = 0, db_path: Optional[str] = None) -> Dict[str, Any]:
    """保存企业微信配置"""
    with get_connection(db_path) as conn:
        existing = conn.execute("SELECT id FROM wecom_config WHERE id = 1").fetchone()
        if existing:
            conn.execute(
                "UPDATE wecom_config SET corp_id=?, agent_id=?, secret=?, webhook_url=?, is_active=? WHERE id=1",
                (corp_id, agent_id, secret, webhook_url, is_active)
            )
        else:
            conn.execute(
                "INSERT INTO wecom_config (id, corp_id, agent_id, secret, webhook_url, is_active) VALUES (1, ?, ?, ?, ?, ?)",
                (corp_id, agent_id, secret, webhook_url, is_active)
            )
        return get_wecom_config(db_path)


def get_feishu_config(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """获取飞书配置"""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM feishu_config WHERE id = 1"
        ).fetchone()
        if not row:
            return {"app_id": "", "app_secret": "", "verify_token": "", "is_active": 0}
        return _row_to_dict(row)


def save_feishu_config(app_id: str, app_secret: str, verify_token: str,
                       is_active: int = 0, db_path: Optional[str] = None) -> Dict[str, Any]:
    """保存飞书配置"""
    with get_connection(db_path) as conn:
        existing = conn.execute("SELECT id FROM feishu_config WHERE id = 1").fetchone()
        if existing:
            conn.execute(
                "UPDATE feishu_config SET app_id=?, app_secret=?, verify_token=?, is_active=? WHERE id=1",
                (app_id, app_secret, verify_token, is_active)
            )
        else:
            conn.execute(
                "INSERT INTO feishu_config (id, app_id, app_secret, verify_token, is_active) VALUES (1, ?, ?, ?, ?)",
                (app_id, app_secret, verify_token, is_active)
            )
        return get_feishu_config(db_path)


def check_any_configured(db_path: Optional[str] = None) -> Dict[str, bool]:
    """检查各项配置是否已配置"""
    with get_connection(db_path) as conn:
        api = conn.execute("SELECT COUNT(*) FROM api_config WHERE is_active=1 AND api_key!=''").fetchone()[0]
        wecom = conn.execute("SELECT COUNT(*) FROM wecom_config WHERE is_active=1").fetchone()[0]
        feishu = conn.execute("SELECT COUNT(*) FROM feishu_config WHERE is_active=1").fetchone()[0]
        return {
            "ai_configured": api > 0,
            "wecom_configured": wecom > 0,
            "feishu_configured": feishu > 0,
            "any_configured": api > 0 or wecom > 0 or feishu > 0
        }


# ==================== 工具函数 ====================

def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """将sqlite3.Row转为字典"""
    if row is None:
        return None
    return dict(row)


# ==================== 生产日志操作 ====================

def list_production_logs(
    task_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """获取生产日志列表"""
    conditions = []
    params = []
    if task_id:
        conditions.append("pl.task_id = ?")
        params.append(task_id)
    if status:
        conditions.append("pl.status = ?")
        params.append(status)
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    with get_connection(db_path) as conn:
        count_row = conn.execute(
            f"SELECT COUNT(*) FROM production_logs pl {where_clause}", params
        ).fetchone()
        total = count_row[0]
        
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"""SELECT pl.*, o.order_no, ot.task_name
                FROM production_logs pl
                JOIN order_tasks ot ON pl.task_id = ot.id
                JOIN orders o ON ot.order_id = o.id
                {where_clause}
                ORDER BY pl.created_at DESC
                LIMIT ? OFFSET ?""",
            params + [page_size, offset]
        ).fetchall()
        
        return {
            "logs": [_row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size
        }


def confirm_production_log(log_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """确认生产日志（人工复核通过）"""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE production_logs SET status = 'confirmed' WHERE id = ?",
            (log_id,)
        )
        row = conn.execute(
            "SELECT * FROM production_logs WHERE id = ?", (log_id,)
        ).fetchone()
        return _row_to_dict(row)


def reject_production_log(log_id: int, reason: str = "", db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """拒绝生产日志（AI识别有误）"""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE production_logs SET status = 'rejected', notes = ? WHERE id = ?",
            (reason, log_id)
        )
        row = conn.execute(
            "SELECT * FROM production_logs WHERE id = ?", (log_id,)
        ).fetchone()
        return _row_to_dict(row)


# ==================== 逾期预警 ====================

def get_overdue_orders(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取逾期订单（交货日期已过但未完成）"""
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
        return [_row_to_dict(r) for r in rows]


def get_upcoming_delivery(days: int = 3, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取即将到期的订单（未来N天内交货）"""
    from datetime import timedelta
    soon = (datetime.date.today() + timedelta(days=days)).isoformat()
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
        return [_row_to_dict(r) for r in rows]
