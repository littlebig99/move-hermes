"""
产品管理 API
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
import database as db

router = APIRouter(prefix="/api/products", tags=["产品管理"])


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


@router.get("", response_model=dict)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """获取产品列表"""
    result = db.list_products(page=page, page_size=page_size)
    
    if category:
        result["products"] = [p for p in result["products"] if p.get("category") == category]
        result["total"] = len(result["products"])
    
    if search:
        result["products"] = [
            p for p in result["products"]
            if search.lower() in p.get("name", "").lower() or
               search.lower() in p.get("spec", "").lower()
        ]
        result["total"] = len(result["products"])
    
    return result


@router.post("", response_model=dict)
async def create_product(product: ProductCreate):
    """创建产品"""
    return db.create_product(
        name=product.name,
        spec=product.spec,
        unit=product.unit,
        category=product.category
    )


@router.get("/{product_id}", response_model=dict)
async def get_product(product_id: int):
    """获取产品详情"""
    result = db.get_product(product_id)
    if not result:
        raise HTTPException(404, f"产品 {product_id} 不存在")
    return result


@router.put("/{product_id}", response_model=dict)
async def update_product(product_id: int, update: ProductUpdate):
    """更新产品"""
    existing = db.get_product(product_id)
    if not existing:
        raise HTTPException(404, f"产品 {product_id} 不存在")
    
    result = db.update_product(product_id, update.model_dump(exclude_none=True))
    return result


@router.delete("/{product_id}")
async def delete_product(product_id: int):
    """删除产品"""
    if not db.delete_product(product_id):
        raise HTTPException(404, f"产品 {product_id} 不存在")
    return {"message": "产品已删除", "id": product_id}
