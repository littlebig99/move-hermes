"""
订单管理 API — 完整的订单 CRUD + 工序管理 + 看板数据
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import datetime
import database as db

router = APIRouter(prefix="/api/orders", tags=["订单管理"])


# ==================== 请求/响应模型 ====================

class OrderCreate(BaseModel):
    customer_id: int
    product_id: int
    quantity: float = Field(..., gt=0)
    unit_price: Optional[float] = None
    priority: str = "normal"
    notes: Optional[str] = None
    delivery_date: Optional[str] = None
    order_no: Optional[str] = None


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    delivery_date: Optional[str] = None
    
    @field_validator('priority', mode='before')
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        """验证优先级字段只能为 normal 或 urgent"""
        if v is None:
            return v
        valid_values = {'normal', 'urgent'}
        if v.lower() not in valid_values:
            raise ValueError(f"priority 必须是 'normal' 或 'urgent'，当前值: {v}")
        return v.lower()


class TaskCreate(BaseModel):
    task_name: str
    sequence_num: int
    worker_id: Optional[int] = None
    worker_name: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    status: str
    worker_id: Optional[int] = None
    worker_name: Optional[str] = None
    photo_url: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_notes: Optional[str] = None


# ==================== 订单CRUD ====================

@router.post("", response_model=dict)
async def create_order(order: OrderCreate):
    """创建新订单"""
    # 验证客户是否存在
    customer = db.get_customer(order.customer_id)
    if not customer:
        raise HTTPException(404, f"客户ID {order.customer_id} 不存在")
    
    # 验证产品是否存在
    product = db.get_product(order.product_id)
    if not product:
        raise HTTPException(404, f"产品ID {order.product_id} 不存在")
    
    try:
        result = db.create_order(
            customer_id=order.customer_id,
            product_id=order.product_id,
            quantity=order.quantity,
            unit_price=order.unit_price,
            priority=order.priority,
            notes=order.notes,
            delivery_date=order.delivery_date,
            order_no=order.order_no
        )
        return result
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(400, f"订单编号 {order.order_no} 已存在")
        raise HTTPException(500, f"创建订单失败: {str(e)}")


@router.get("", response_model=dict)
async def list_orders(
    status: Optional[str] = Query(None, description="按状态筛选"),
    priority: Optional[str] = Query(None, description="按优先级筛选"),
    customer_id: Optional[int] = Query(None, description="按客户筛选"),
    search: Optional[str] = Query(None, description="搜索订单号/客户/备注"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取订单列表"""
    return db.list_orders(
        status=status,
        priority=priority,
        customer_id=customer_id,
        search=search,
        page=page,
        page_size=page_size
    )


@router.get("/search/{order_no}")
async def search_order_by_no(order_no: str):
    """通过订单编号搜索"""
    with db.get_connection() as conn:
        row = conn.execute(
            """SELECT o.*, c.name as customer_name, p.name as product_name
               FROM orders o
               LEFT JOIN customers c ON o.customer_id = c.id
               LEFT JOIN products p ON o.product_id = p.id
               WHERE o.order_no = ?""",
            (order_no,)
        ).fetchone()
        if not row:
            raise HTTPException(404, f"订单 {order_no} 不存在")
        result = db._row_to_dict(row)
        result["tasks"] = conn.execute(
            "SELECT * FROM order_tasks WHERE order_id = ? ORDER BY sequence_num",
            (result["id"],)
        ).fetchall()
        return result


@router.get("/{order_id}", response_model=dict)
async def get_order(order_id: int):
    """获取订单详情"""
    order = db.get_order(order_id)
    if not order:
        raise HTTPException(404, f"订单 {order_id} 不存在")
    return order


@router.put("/{order_id}", response_model=dict)
async def update_order(order_id: int, update: OrderUpdate):
    """更新订单"""
    existing = db.get_order(order_id)
    if not existing:
        raise HTTPException(404, f"订单 {order_id} 不存在")
    
    result = db.update_order(order_id, update.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(400, "没有可更新的字段")
    return result


@router.delete("/{order_id}")
async def delete_order(order_id: int):
    """删除订单"""
    if not db.delete_order(order_id):
        raise HTTPException(404, f"订单 {order_id} 不存在")
    return {"message": "订单已删除", "id": order_id}


@router.post("/{order_id}/urgent")
async def mark_urgent(order_id: int):
    """标记加急"""
    existing = db.get_order(order_id)
    if not existing:
        raise HTTPException(404, f"订单 {order_id} 不存在")
    
    return db.update_order(order_id, {"priority": "urgent"})


# ==================== 工序管理 ====================

@router.get("/{order_id}/tasks")
async def get_order_tasks(order_id: int):
    """获取订单的所有工序"""
    if not db.get_order(order_id):
        raise HTTPException(404, f"订单 {order_id} 不存在")
    
    tasks = db.get_order_tasks(order_id)
    return {"order_id": order_id, "tasks": tasks}


@router.post("/{order_id}/tasks")
async def add_task(order_id: int, task: TaskCreate):
    """添加新工序"""
    if not db.get_order(order_id):
        raise HTTPException(404, f"订单 {order_id} 不存在")
    
    return db.add_task(order_id, task.task_name, task.sequence_num, task.worker_id)


@router.put("/tasks/{task_id}/status")
async def update_task_status(task_id: int, status_update: TaskStatusUpdate):
    """更新工序状态"""
    result = db.update_task_status(
        task_id=task_id,
        status=status_update.status,
        worker_id=status_update.worker_id,
        worker_name=status_update.worker_name,
        photo_url=status_update.photo_url,
        ai_confidence=status_update.ai_confidence,
        ai_notes=status_update.ai_notes
    )
    
    if not result:
        raise HTTPException(404, f"工序 {task_id} 不存在")
    
    return result


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    """删除工序"""
    if not db.delete_task(task_id):
        raise HTTPException(404, f"工序 {task_id} 不存在")
    return {"message": "工序已删除", "id": task_id}


@router.get("/tasks/stalled")
async def get_stalled_tasks(threshold_days: int = Query(2, ge=1, le=30)):
    """获取呆滞工序列表"""
    return {
        "stalled_tasks": db.get_stalled_tasks(threshold_days),
        "threshold_days": threshold_days
    }


# ==================== 看板数据 ====================

@router.get("/export/csv")
async def export_orders_csv():
    """导出订单为CSV"""
    import csv
    import io
    
    orders = db.list_orders(page=1, page_size=1000)["orders"]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["订单编号", "客户", "产品", "数量", "单价", "总额", "状态", "优先级", "交货日期", "备注"])
    
    for o in orders:
        writer.writerow([
            o.get("order_no", ""),
            o.get("customer_name", ""),
            o.get("product_name", ""),
            o.get("quantity", ""),
            o.get("unit_price", ""),
            o.get("total_amount", ""),
            o.get("status", ""),
            o.get("priority", ""),
            o.get("delivery_date", ""),
            o.get("notes", "")
        ])
    
    from fastapi import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=orders.csv"}
    )


@router.get("/stats")
async def get_stats():
    """获取看板统计数据"""
    return db.get_dashboard_stats()


@router.get("/production")
async def get_production_board():
    """获取生产进度看板"""
    return db.get_dashboard_production()


# ==================== 预警API ====================

@router.get("/alerts/overdue")
async def get_overdue():
    """获取逾期订单"""
    return {"overdue_orders": db.get_overdue_orders()}


@router.get("/alerts/upcoming")
async def get_upcoming(days: int = Query(3, ge=1, le=14)):
    """获取即将到期订单"""
    return {"upcoming_orders": db.get_upcoming_delivery(days)}


@router.get("/alerts/all")
async def get_all_alerts():
    """获取所有预警（呆滞 + 逾期 + 即将到期）"""
    return {
        "stalled": db.get_stalled_tasks(2),
        "overdue": db.get_overdue_orders(),
        "upcoming": db.get_upcoming_delivery(3)
    }
