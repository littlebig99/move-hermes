"""
Move Hermes — 智能订单管理系统
主入口：FastAPI应用
"""
import os
import sys
import uvicorn
from pathlib import Path

# 确保项目根目录在路径中
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Move Hermes",
    description="U盘智能体 — 小企业AI订单管理系统",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 路径配置 ====================

def get_data_dir():
    """获取数据目录（U盘上的data文件夹）"""
    script_dir = PROJECT_ROOT
    data_dir = script_dir / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir

def get_db_path():
    """获取数据库路径"""
    return get_data_dir() / "move_hermes.db"

def get_static_dir():
    """获取前端静态资源目录"""
    return PROJECT_ROOT / "frontend"

def get_api_config():
    """获取API配置"""
    config_path = get_data_dir() / "api_config.json"
    if config_path.exists():
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# ==================== 健康检查 ====================

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "version": "0.1.0",
        "data_dir": str(get_data_dir()),
        "db_path": str(get_db_path())
    }

# ==================== 前端页面路由 ====================

@app.get("/")
async def root():
    """重定向到看板首页"""
    return FileResponse(get_static_dir() / "dashboard.html")

@app.get("/config")
async def config_page():
    """配置页面（首次启动）"""
    return FileResponse(get_static_dir() / "config.html")

@app.get("/dashboard")
async def dashboard_page():
    """看板首页"""
    return FileResponse(get_static_dir() / "dashboard.html")

@app.get("/orders")
async def orders_page():
    """订单列表"""
    return FileResponse(get_static_dir() / "orders.html")

@app.get("/customers")
async def customers_page():
    """客户管理"""
    return FileResponse(get_static_dir() / "customers.html")

@app.get("/products")
async def products_page():
    """产品管理"""
    return FileResponse(get_static_dir() / "products.html")

@app.get("/alerts")
async def alerts_page():
    """预警中心"""
    return FileResponse(get_static_dir() / "alerts.html")

# ==================== 静态文件服务 ====================

@app.get("/static/{path:path}")
async def serve_static(path: str):
    """提供静态文件"""
    file_path = get_static_dir() / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return {"error": "File not found"}

# ==================== 启动入口 ====================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Move Hermes 正在启动...")
    print(f"   数据目录: {get_data_dir()}")
    print(f"   数据库: {get_db_path()}")
    print(f"   访问地址: http://localhost:{port}")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info"
    )
