"""
照片上传与AI识别 API
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import base64
import json
import datetime
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

router = APIRouter(prefix="/api/photos", tags=["照片与AI识别"])


class ParseResult(BaseModel):
    """AI解析结果"""
    order_no: Optional[str] = None
    customer: Optional[str] = None
    product: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = "件"
    unit_price: Optional[float] = None
    delivery_date: Optional[str] = None
    priority: Optional[str] = "normal"
    notes: Optional[str] = None
    confidence: float = 0.0


class TaskParseResult(BaseModel):
    """工单解析结果"""
    task_name: Optional[str] = None
    quantity: Optional[float] = None
    worker_name: Optional[str] = None
    notes: Optional[str] = None
    confidence: float = 0.0


def _ensure_photo_dir(db_path: Optional[str] = None) -> Path:
    """确保照片目录存在"""
    if db_path:
        data_dir = Path(db_path).parent
    else:
        data_dir = Path(__file__).parent.parent / "data"
    photo_dir = data_dir / "photos"
    photo_dir.mkdir(exist_ok=True)
    return photo_dir


@router.post("/upload")
async def upload_photo(
    file: UploadFile = File(...),
    purpose: str = Form("order"),  # order | production
    order_id: Optional[int] = Form(None),
    task_id: Optional[int] = Form(None)
):
    """上传图片"""
    # 验证文件类型
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"不支持的文件类型: {file.content_type}")
    
    # 读取文件
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB限制
        raise HTTPException(400, "图片过大，最大10MB")
    
    # 保存文件
    photo_dir = _ensure_photo_dir()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    filename = f"{purpose}_{timestamp}_{os.urandom(4).hex()}{ext}"
    filepath = photo_dir / filename
    
    with open(filepath, "wb") as f:
        f.write(content)
    
    # 如果是生产工单照片，记录日志
    if purpose == "production" and task_id:
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO production_logs (task_id, photo_url, status) VALUES (?, ?, 'pending_review')",
                (task_id, f"/data/photos/{filename}")
            )
    
    return {
        "success": True,
        "filename": filename,
        "url": f"/data/photos/{filename}",
        "size": len(content),
        "purpose": purpose
    }


@router.post("/parse")
async def parse_photo(
    file: UploadFile = File(...),
    purpose: str = Form("order")
):
    """
    上传并立即触发AI识别（优先AI，失败则降级到本地OCR）
    
    返回:
    - order: 订单识别结果
    - production: 工单识别结果
    """
    content = await file.read()
    
    # 转base64
    b64 = base64.b64encode(content).decode("utf-8")
    data_url = f"data:{file.content_type};base64,{b64}"
    
    # 获取AI配置
    config = db.get_api_config()
    
    if config and config.get("api_key"):
        # 有AI配置，优先调用AI
        from services.ai_service import AIService
        ai = AIService({
            "provider": config["provider"],
            "api_key": config["api_key"],
            "model": config["model"],
            "base_url": config.get("base_url")
        })
        
        try:
            if purpose == "order":
                result = await ai.parse_order_photo(b64)
            else:
                result = await ai.parse_production_photo(b64)
            
            if isinstance(result, dict) and "error" in result:
                # AI失败，降级到OCR
                if HAS_LOCAL_OCR:
                    result = await _local_parse(b64, purpose)
                    result["source"] = "ocr_fallback"
                else:
                    return {
                        "success": False,
                        "error": result["error"],
                        "source": "ai_failed"
                    }
            else:
                result["source"] = "ai"
            
            return {
                "success": True,
                "purpose": purpose,
                "data": result
            }
        except Exception as e:
            # AI异常，降级到OCR
            if HAS_LOCAL_OCR:
                result = await _local_parse(b64, purpose)
                result["source"] = "ocr_fallback"
                return {
                    "success": True,
                    "purpose": purpose,
                    "data": result
                }
            return {
                "success": False,
                "error": f"AI识别失败: {str(e)}"
            }
    else:
        # 无AI配置，直接使用本地OCR
        if HAS_LOCAL_OCR:
            result = await _local_parse(b64, purpose)
            result["source"] = "ocr"
            return {
                "success": True,
                "purpose": purpose,
                "data": result,
                "message": "使用本地OCR识别（未配置AI API）"
            }
        return {
            "success": False,
            "error": "未配置AI API且OCR不可用，请在配置页面设置API Key或安装tesseract"
        }


# ==================== 本地OCR端点 ====================

HAS_LOCAL_OCR = False
try:
    import pytesseract
    from PIL import Image
    import tempfile
    HAS_LOCAL_OCR = True
    from ocr_service import extract_text_from_image, parse_order_from_text, parse_production_from_text
except ImportError:
    pass

# 检查OCR可用性
if HAS_LOCAL_OCR:
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        HAS_LOCAL_OCR = False


async def _local_parse(image_b64: str, purpose: str) -> Dict[str, Any]:
    """使用本地OCR解析图片"""
    try:
        img_data = base64.b64decode(image_b64)
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(img_data)
            tmp_path = f.name
        
        try:
            text = extract_text_from_image(tmp_path)
            if purpose == "order":
                return parse_order_from_text(text)
            else:
                return parse_production_from_text(text)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        return {"error": f"OCR失败: {str(e)}"}


@router.post("/auto-create-order")
async def auto_create_order(
    file: UploadFile = File(...),
    customer_name: Optional[str] = Form(None),
    product_name: Optional[str] = Form(None)
):
    """
    上传订单照片 → AI识别 → 自动创建订单
    
    如果提供了customer_name/product_name，用于匹配已有客户和产品
    """
    content = await file.read()
    b64 = base64.b64encode(content).decode("utf-8")
    data_url = f"data:{file.content_type};base64,{b64}"
    
    # 获取AI配置
    config = db.get_api_config()
    if not config:
        return {
            "success": False,
            "error": "未配置AI API"
        }
    
    from services.ai_service import AIService
    ai = AIService({
        "provider": config["provider"],
        "api_key": config["api_key"],
        "model": config["model"],
        "base_url": config.get("base_url")
    })
    
    try:
        parsed = await ai.parse_order_photo(b64)
    except Exception as e:
        return {
            "success": False,
            "error": f"AI识别失败: {str(e)}"
        }
    
    # 查找客户
    customer_id = None
    if customer_name and parsed.get("customer"):
        customers = db.list_customers(search=parsed["customer"])
        for c in customers["customers"]:
            if customer_name in c["name"] or c["name"] in customer_name:
                customer_id = c["id"]
                break
    
    # 查找产品
    product_id = None
    if product_name and parsed.get("product"):
        products = db.list_products(search=parsed["product"])
        for p in products["products"]:
            if product_name in p["name"] or p["name"] in product_name:
                product_id = p["id"]
                break
    
    # 创建订单
    if customer_id and product_id:
        order = db.create_order(
            customer_id=customer_id,
            product_id=product_id,
            quantity=parsed.get("quantity", 0),
            unit_price=parsed.get("unit_price"),
            priority=parsed.get("priority", "normal"),
            notes=parsed.get("notes"),
            delivery_date=parsed.get("delivery_date")
        )
        return {
            "success": True,
            "order": order,
            "parsed": parsed,
            "message": "订单创建成功"
        }
    
    # 如果没找到客户或产品，返回解析结果供手动选择
    return {
        "success": True,
        "parsed": parsed,
        "customer_id": customer_id,
        "product_id": product_id,
        "needs_selection": True,
        "message": "AI识别成功，请选择客户和产品"
    }


@router.get("/recent")
async def get_recent_photos(limit: int = 10):
    """获取最近上传的照片"""
    photo_dir = _ensure_photo_dir()
    if not photo_dir.exists():
        return {"photos": []}
    
    files = sorted(photo_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
    photos = []
    for f in files[:limit]:
        photos.append({
            "filename": f.name,
            "path": f"/data/photos/{f.name}",
            "size": f.stat().st_size,
            "modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        })
    
    return {"photos": photos}


# ==================== 生产日志API ====================

@router.get("/logs")
async def list_production_logs(
    task_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取生产日志列表"""
    return db.list_production_logs(
        task_id=task_id, status=status, page=page, page_size=page_size
    )


@router.post("/logs/{log_id}/confirm")
async def confirm_log(log_id: int):
    """确认生产日志（人工复核通过）"""
    result = db.confirm_production_log(log_id)
    if not result:
        raise HTTPException(404, f"日志 {log_id} 不存在")
    return result


@router.post("/logs/{log_id}/reject")
async def reject_log(log_id: int, reason: str = Form("")):
    """拒绝生产日志"""
    result = db.reject_production_log(log_id, reason)
    if not result:
        raise HTTPException(404, f"日志 {log_id} 不存在")
    return result
