"""Move Hermes — 工序仓库（CRUD）"""
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


def _row_to_dict(row) -> Dict[str, Any]:
    if row is None:
        return None
    return dict(row)


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
                d["stalled_days"] = threshold_days
            result.append(d)
        
        return result
