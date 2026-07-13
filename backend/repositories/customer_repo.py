"""Move Hermes — 客户仓库（CRUD）"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# 兼容直接运行和包导入
try:
    from ..connection import get_connection
except ImportError:
    _parent = str(Path(__file__).resolve().parent.parent)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)
    from connection import get_connection


def _row_to_dict(row) -> Dict[str, Any]:
    if row is None:
        return None
    return dict(row)


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
        result["order_count"] = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE customer_id = ?", (customer_id,)
        ).fetchone()[0]
        return result


def delete_customer(customer_id: int, db_path: Optional[str] = None) -> bool:
    """删除客户"""
    with get_connection(db_path) as conn:
        return conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,)).rowcount > 0
