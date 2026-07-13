"""Move Hermes — 生产日志仓库（CRUD）"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

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
