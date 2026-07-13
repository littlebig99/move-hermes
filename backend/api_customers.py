"""
客户管理 API
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
# 数据库导入（兼容直接运行和包导入）
import sys
from pathlib import Path
try:
    from . import database as db
except ImportError:
    _backend = str(Path(__file__).resolve().parent)
    if _backend not in sys.path:
        sys.path.insert(0, _backend)
    import database as db

router = APIRouter(prefix="/api/customers", tags=["客户管理"])


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


@router.get("", response_model=dict)
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None)
):
    """获取客户列表"""
    result = db.list_customers(page=page, page_size=page_size)
    if search:
        result["customers"] = [
            c for c in result["customers"]
            if search.lower() in c.get("name", "").lower() or
               search.lower() in c.get("phone", "").lower()
        ]
        result["total"] = len(result["customers"])
    return result


@router.post("", response_model=dict)
async def create_customer(customer: CustomerCreate):
    """创建客户"""
    return db.create_customer(
        name=customer.name,
        contact=customer.contact,
        phone=customer.phone,
        address=customer.address
    )


@router.get("/{customer_id}", response_model=dict)
async def get_customer(customer_id: int):
    """获取客户详情"""
    result = db.get_customer(customer_id)
    if not result:
        raise HTTPException(404, f"客户 {customer_id} 不存在")
    return result


@router.put("/{customer_id}", response_model=dict)
async def update_customer(customer_id: int, update: CustomerUpdate):
    """更新客户"""
    existing = db.get_customer(customer_id)
    if not existing:
        raise HTTPException(404, f"客户 {customer_id} 不存在")
    
    result = db.update_customer(customer_id, update.model_dump(exclude_none=True))
    return result


@router.delete("/{customer_id}")
async def delete_customer(customer_id: int):
    """删除客户"""
    if not db.delete_customer(customer_id):
        raise HTTPException(404, f"客户 {customer_id} 不存在")
    return {"message": "客户已删除", "id": customer_id}
