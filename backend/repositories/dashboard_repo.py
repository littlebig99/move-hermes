"""Move Hermes — 看板统计仓库（Dashboard）"""
import datetime
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

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


def get_dashboard_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """获取看板统计数据"""
    with get_connection(db_path) as conn:
        status_counts = {}
        for row in conn.execute(
            "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status"
        ).fetchall():
            status_counts[row["status"]] = row["cnt"]
        
        urgent = conn.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE priority = 'urgent'"
        ).fetchone()["cnt"]
        
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat()
        stalled_count = conn.execute(
            "SELECT COUNT(*) FROM order_tasks WHERE status IN ('pending', 'in_progress') AND started_at < ?",
            (cutoff,)
        ).fetchone()[0]
        
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
