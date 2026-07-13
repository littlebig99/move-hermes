"""Move Hermes — 订单仓库（CRUD）"""
import datetime
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# 兼容直接运行和包导入
try:
    from ..connection import get_connection
except ImportError:
    _parent = str(Path(__file__).resolve().parent.parent)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)
    from connection import get_connection


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


def _row_to_dict(row) -> Dict[str, Any]:
    """将sqlite3.Row转为字典"""
    if row is None:
        return None
    return dict(row)


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


_ALLOWED_ORDER_COLUMNS = {"status", "priority", "customer_id"}


def _build_safe_where(allowed_columns: set, conditions: list, params: list) -> str:
    """构建安全的 WHERE 子句 — 只允许白名单中的列名"""
    for cond in conditions:
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
        count_row = conn.execute(
            f"SELECT COUNT(*) FROM orders o {where_clause}", params
        ).fetchone()
        total = count_row[0]
        
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
        cust_row = conn.execute(
            "SELECT name FROM customers WHERE id = ?", (result.get("customer_id"),)
        ).fetchone()
        result["customer_name"] = cust_row[0] if cust_row else None
        prod_row = conn.execute(
            "SELECT name FROM products WHERE id = ?", (result.get("product_id"),)
        ).fetchone()
        result["product_name"] = prod_row[0] if prod_row else None
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
