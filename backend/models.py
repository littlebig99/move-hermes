"""Move Hermes — 数据模型定义（Pydantic + 枚举）"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ==================== 状态枚举 ====================

class OrderStatus(str, Enum):
    PENDING = "pending"
    PRODUCING = "producing"
    COMPLETED = "completed"
    SHIPPED = "shipped"


class OrderPriority(str, Enum):
    NORMAL = "normal"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ProductionLogStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


# ==================== 请求模型 ====================

class OrderCreate(BaseModel):
    customer_id: int
    product_id: int
    quantity: float = Field(gt=0)
    unit_price: Optional[float] = None
    priority: OrderPriority = OrderPriority.NORMAL
    notes: Optional[str] = None
    delivery_date: Optional[str] = None
    order_no: Optional[str] = None


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    priority: Optional[OrderPriority] = None
    notes: Optional[str] = None
    delivery_date: Optional[str] = None


class CustomerCreate(BaseModel):
    name: str
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class ProductCreate(BaseModel):
    name: str
    spec: Optional[str] = None
    unit: str = "件"
    category: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    spec: Optional[str] = None
    unit: Optional[str] = None
    category: Optional[str] = None


class TaskCreate(BaseModel):
    order_id: int
    task_name: str
    sequence_num: int


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    worker_id: Optional[int] = None
    worker_name: Optional[str] = None
    photo_url: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_notes: Optional[str] = None


class ApiConfigInput(BaseModel):
    provider: str
    api_key: str
    model: str = "gpt-4o-mini"
    base_url: Optional[str] = None


class WeComConfigInput(BaseModel):
    corp_id: str = ""
    agent_id: str = ""
    secret: str = ""
    webhook_url: str = ""
    is_active: int = 0


class FeiShuConfigInput(BaseModel):
    app_id: str = ""
    app_secret: str = ""
    verify_token: str = ""
    is_active: int = 0


class ProductionLogQuery(BaseModel):
    task_id: Optional[int] = None
    status: Optional[str] = None
    page: int = 1
    page_size: int = 20


class OrderListQuery(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    customer_id: Optional[int] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 20


# ==================== 响应模型 ====================

class OrderResponse(BaseModel):
    id: int
    order_no: str
    customer_id: int
    product_id: int
    quantity: float
    unit_price: Optional[float] = None
    total_amount: float
    status: str
    priority: str
    notes: Optional[str] = None
    delivery_date: Optional[str] = None
    created_at: str
    updated_at: str
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    tasks: List[Dict[str, Any]] = []


class TaskResponse(BaseModel):
    id: int
    order_id: int
    task_name: str
    sequence_num: int
    status: str
    worker_id: Optional[int] = None
    worker_name: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    photo_url: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_notes: Optional[str] = None


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
