"""
订单管理 API — MVP 核心接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import datetime

router = APIRouter(prefix="/api/orders", tags=["订单管理"])

# ==================== 数据模型 ====================

class OrderCreate(BaseModel):
    order_no: Optional[str] = None
    customer_id: int
    product_id: int
    quantity: float
    unit_price: Optional[float] = None
    priority: str = "normal"  # normal | urgent
    notes: Optional[str] = None

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None

class TaskCreate(BaseModel):
    task_name: str
    sequence_num: int
    worker_id: Optional[int] = None

class TaskStatusUpdate(BaseModel):
    status: str  # pending | in_progress | completed
    worker_id: Optional[int] = None
    photo_url: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_notes: Optional[str] = None

# ==================== 订单CRUD ====================

@router.post("")
async def create_order(order: OrderCreate):
    """创建新订单"""
    # 自动生成订单号
    if not order.order_no:
        today = datetime.date.today().strftime("%Y%m%d")
        # 简单递增逻辑，实际应从数据库查询最大序号
        order_no = f"ORD-{today}-001"
    else:
        order_no = order.order_no
    
    return {
        "id": 1,
        "order_no": order_no,
        "status": "pending",
        "message": "订单创建成功"
    }

@router.get("")
async def list_orders(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """获取订单列表"""
    return {
        "orders": [],
        "total": 0,
        "page": page,
        "page_size": page_size
    }

@router.get("/{order_id}")
async def get_order(order_id: int):
    """获取订单详情"""
    return {
        "id": order_id,
        "order_no": "ORD-20260623-001",
        "status": "producing",
        "priority": "normal",
        "tasks": []
    }

@router.put("/{order_id}")
async def update_order(order_id: int, update: OrderUpdate):
    """更新订单"""
    return {"message": "订单更新成功", "id": order_id}

@router.delete("/{order_id}")
async def delete_order(order_id: int):
    """删除订单"""
    return {"message": "订单已删除", "id": order_id}

@router.post("/{order_id}/urgent")
async def mark_urgent(order_id: int):
    """标记加急"""
    return {"message": "已标记为加急", "order_id": order_id, "priority": "urgent"}

# ==================== 工序管理 ====================

@router.get("/{order_id}/tasks")
async def get_order_tasks(order_id: int):
    """获取订单的所有工序"""
    return {
        "order_id": order_id,
        "tasks": [
            {"id": 1, "task_name": "下料", "sequence_num": 1, "status": "completed"},
            {"id": 2, "task_name": "加工", "sequence_num": 2, "status": "in_progress"},
            {"id": 3, "task_name": "组装", "sequence_num": 3, "status": "pending"},
            {"id": 4, "task_name": "质检", "sequence_num": 4, "status": "pending"},
            {"id": 5, "task_name": "包装", "sequence_num": 5, "status": "pending"},
        ]
    }

@router.post("/{order_id}/tasks")
async def add_task(order_id: int, task: TaskCreate):
    """添加新工序"""
    return {"message": "工序已添加", "order_id": order_id, "task": task.dict()}

@router.put("/tasks/{task_id}/status")
async def update_task_status(task_id: int, status_update: TaskStatusUpdate):
    """更新工序状态"""
    return {
        "message": "工序状态已更新",
        "task_id": task_id,
        "status": status_update.status
    }

@router.get("/tasks/stalled")
async def get_stalled_tasks(days: int = 1):
    """获取呆滞工序列表"""
    return {
        "stalled_tasks": [],
        "threshold_days": days
    }

# ==================== 看板数据 ====================

@router.get("/stats")
async def get_stats():
    """获取看板统计数据"""
    return {
        "in_production": 12,
        "pending": 5,
        "completed": 8,
        "urgent": 3,
        "stalled": 3
    }
