"""Move Hermes — 产品仓库（CRUD）"""
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
