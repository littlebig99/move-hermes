"""
Move Hermes — 智能订单管理系统
主入口：FastAPI应用
"""
import os
import sys
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

# ==================== 路径配置 ====================

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = PROJECT_ROOT / "data"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# 确保数据目录存在
DATA_DIR.mkdir(exist_ok=True)

# 数据库初始化（兼容直接运行和包导入）
try:
    from . import database as db
except ImportError:
    import database as db
db.init_db()

# ==================== 应用创建 ====================

app = FastAPI(
    title="Move Hermes",
    description="U盘智能体 — 小企业AI订单管理系统",
    version="0.1.0"
)

# CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ==================== 导入路由 ====================

# 路由导入（兼容直接运行和包导入）
try:
    from .api_orders import router as orders_router
    from .api_customers import router as customers_router
    from .api_products import router as products_router
    from .api_photos import router as photos_router
    from .api_config import router as config_router
    from .api_webhooks import router as webhooks_router
except ImportError:
    from api_orders import router as orders_router
    from api_customers import router as customers_router
    from api_products import router as products_router
    from api_photos import router as photos_router
    from api_config import router as config_router
    from api_webhooks import router as webhooks_router

app.include_router(orders_router)
app.include_router(customers_router)
app.include_router(products_router)
app.include_router(photos_router)
app.include_router(config_router)
app.include_router(webhooks_router)


# ==================== 前端页面路由 ====================

PAGE_FILES = {
    "/": "dashboard.html",
    "/config": "config.html",
    "/dashboard": "dashboard.html",
    "/orders": "orders.html",
    "/customers": "customers.html",
    "/products": "products.html",
    "/alerts": "alerts.html",
    "/order-detail": "order-detail.html",
    "/tasks": "tasks.html",
    "/finance": "finance.html",
    "/recognize": "recognize.html",
    "/卷料长度计算": "卷料长度计算.html",
}


def _is_configured() -> bool:
    """检查 AI 配置是否存在"""
    try:
        return db.get_api_config() is not None
    except Exception:
        return False


for route, page in PAGE_FILES.items():
    @app.get(route)
    async def _route_page(_page=page, _route=route):
        # 除 /config 和 /health 外，其他页面都检查配置
        if _route not in ("/config", "/health"):
            if not _is_configured():
                return RedirectResponse(url="/config", status_code=302)
        
        fp = FRONTEND_DIR / _page
        if fp.exists():
            return FileResponse(fp)
        return {"error": f"Page {_page} not found"}


# ==================== 静态文件服务 ====================

# 前端静态文件
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# 上传的照片文件
PHOTO_DIR = DATA_DIR / "photos"
PHOTO_DIR.mkdir(exist_ok=True)
if PHOTO_DIR.exists():
    app.mount("/data/photos", StaticFiles(directory=str(PHOTO_DIR)), name="photos")


@app.get("/data/photos/{filename}")
async def serve_photo(filename: str):
    """提供上传的照片"""
    filepath = PHOTO_DIR / filename
    if filepath.exists() and filepath.is_file():
        return FileResponse(filepath)
    raise HTTPException(404, "照片不存在")


# ==================== 健康检查 ====================

@app.get("/health")
async def health_check():
    """健康检查端点 — 不暴露内部路径"""
    from services.disk_monitor import get_storage_overview
    
    storage = get_storage_overview(str(DATA_DIR))
    
    return {
        "status": "ok",
        "version": "0.1.0",
        "ai_configured": _is_configured(),
        "storage": storage["disk"]
    }


# ==================== 磁盘监控 API ====================

from fastapi import APIRouter
disk_router = APIRouter(prefix="/api/storage", tags=["存储监控"])


@disk_router.get("/")
async def get_storage_status():
    """获取存储状态概览"""
    from services.disk_monitor import get_storage_overview
    return get_storage_overview(str(DATA_DIR))


@disk_router.post("/cleanup")
async def cleanup_photos(days: int = 30):
    """清理旧照片释放空间
    
    Args:
        days: 保留最近N天的照片，默认30天
    """
    from services.disk_monitor import cleanup_old_photos
    result = cleanup_old_photos(str(DATA_DIR), keep_recent_days=days)
    return {
        "success": True,
        "message": f"已清理 {result['deleted_count']} 张照片，释放 {result['freed_mb']}MB 空间",
        **result
    }


# ==================== 错误处理 ====================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404处理 — 前端路由 fallback"""
    if request.url.path.startswith("/api/"):
        return {"error": "Not Found", "path": str(request.url.path)}
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """500处理"""
    return {"error": "Internal Server Error", "detail": str(exc)}


# ==================== 启动入口 ====================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print("=" * 50)
    print("  [OK] Move Hermes — 智能订单管理系统")
    print("=" * 50)
    print(f"  数据目录: {DATA_DIR}")
    print(f"  访问地址: http://localhost:{port}")
    print("=" * 50)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info"
    )
