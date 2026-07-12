"""
配置管理 API — AI / 企业微信 / 飞书
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import database as db

router = APIRouter(prefix="/api/config", tags=["系统配置"])


# ==================== 数据模型 ====================

class AIConfigInput(BaseModel):
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


class FeishuConfigInput(BaseModel):
    app_id: str = ""
    app_secret: str = ""
    verify_token: str = ""
    is_active: int = 0


# ==================== 预设配置 ====================

PRESET_PROVIDERS = [
    {"value": "openai", "label": "OpenAI", "icon": "🟢", "models": ["gpt-4o-mini", "gpt-4o", "gpt-4o-2024-05-13"], "default_url": "https://api.openai.com/v1"},
    {"value": "azure", "label": "Azure OpenAI", "icon": "🔵", "models": ["gpt-4o", "gpt-4o-mini", "gpt-35-turbo"], "default_url": None},
    {"value": "claude", "label": "Anthropic Claude", "icon": "🟠", "models": ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-haiku-3-5"], "default_url": "https://api.anthropic.com/v1"},
    {"value": "zhipu", "label": "智谱 AI (GLM)", "icon": "🔷", "models": ["glm-4-plus", "glm-4", "glm-4-air", "glm-4-airx", "glm-4-flash"], "default_url": "https://open.bigmodel.cn/api/paas/v4"},
    {"value": "dashscope", "label": "阿里云 (通义)", "icon": "🔶", "models": ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-vl-max"], "default_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"value": "deepseek", "label": "DeepSeek", "icon": "⚡", "models": ["deepseek-chat", "deepseek-coder", "deepseek-v3"], "default_url": "https://api.deepseek.com/v1"},
    {"value": "moonshot", "label": "月之暗面 (Kimi)", "icon": "🌙", "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"], "default_url": "https://api.moonshot.cn/v1"},
    {"value": "baichuan", "label": "百川智能", "icon": "🌊", "models": ["Baichuan4", "Baichuan3-Turbo"], "default_url": "https://api.baichuan-ai.com/v1"},
    {"value": "minimax", "label": "MiniMax (海螺)", "icon": "💬", "models": ["abab6.5-chat", "abab6.5s-chat", "abab5.5s"], "default_url": "https://api.minimax.chat/v1"},
    {"value": "ollama", "label": "Ollama (本地)", "icon": "🐑", "models": ["qwen2.5:7b", "llama3.3", "gemma2:9b"], "default_url": "http://localhost:11434/v1"},
    {"value": "custom", "label": "自定义 API", "icon": "⚙️", "models": [], "default_url": None},
]


# ==================== AI 配置 ====================

@router.get("/status", response_model=dict)
async def get_config_status():
    """检查所有配置状态"""
    status = db.check_any_configured()
    api_cfg = db.get_api_config()
    wecom_cfg = db.get_wecom_config()
    feishu_cfg = db.get_feishu_config()
    
    return {
        **status,
        "ai_provider": api_cfg["provider"] if api_cfg else None,
        "ai_model": api_cfg["model"] if api_cfg else None,
        "wecom_active": wecom_cfg.get("is_active", 0) == 1,
        "feishu_active": feishu_cfg.get("is_active", 0) == 1,
        "requires_ai": not status.get("ai_configured", False),
    }


@router.get("/providers", response_model=dict)
async def get_providers():
    """获取所有支持的 AI 提供商预设"""
    return {"providers": PRESET_PROVIDERS}


@router.post("/ai/save", response_model=dict)
async def save_ai_config(input: AIConfigInput):
    """保存 AI API 配置"""
    if not input.api_key or not input.api_key.strip():
        raise HTTPException(400, "API Key 不能为空")
    
    try:
        result = db.save_api_config(
            provider=input.provider,
            api_key=input.api_key,
            model=input.model,
            base_url=input.base_url
        )
        return {
            "success": True,
            "message": "AI 配置已保存",
            "provider": result["provider"],
            "model": result["model"]
        }
    except Exception as e:
        raise HTTPException(500, f"保存配置失败: {str(e)}")


@router.get("/ai/", response_model=dict)
async def get_ai_config():
    """获取当前 AI 配置"""
    config = db.get_api_config()
    if not config:
        return {"configured": False}
    return {
        "configured": True,
        "provider": config["provider"],
        "model": config["model"],
        "base_url": config.get("base_url"),
        "api_key_masked": config["api_key"]  # ***
    }


@router.post("/ai/test")
async def test_ai_connection():
    """测试 AI 连接"""
    config = db.get_api_config()
    if not config:
        raise HTTPException(400, "请先配置 AI API")
    
    from services.ai_service import AIService
    ai = AIService({
        "provider": config["provider"],
        "api_key": config["api_key"],
        "model": config["model"],
        "base_url": config.get("base_url")
    })
    
    try:
        result = await ai.test_connection()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 企业微信配置 ====================

@router.post("/wecom/save", response_model=dict)
async def save_wecom_config(input: WeComConfigInput):
    """保存企业微信配置"""
    try:
        result = db.save_wecom_config(
            corp_id=input.corp_id,
            agent_id=input.agent_id,
            secret=input.secret,
            webhook_url=input.webhook_url,
            is_active=input.is_active
        )
        return {"success": True, "message": "企微配置已保存"}
    except Exception as e:
        raise HTTPException(500, f"保存配置失败: {str(e)}")


@router.get("/wecom/", response_model=dict)
async def get_wecom_config():
    """获取企业微信配置"""
    config = db.get_wecom_config()
    return {"configured": bool(config.get("secret")), "data": config}


@router.post("/wecom/test")
async def test_wecom_connection():
    """测试企业微信连接"""
    config = db.get_wecom_config()
    if not config.get("secret"):
        raise HTTPException(400, "请先配置企业微信 Secret")
    
    try:
        import aiohttp
        # 获取 access_token
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={config['corp_id']}&corpsecret={config['secret']}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                data = await resp.json()
                if "errcode" in data and data["errcode"] != 0:
                    return {"success": False, "error": data.get("errmsg", "未知错误")}
                return {"success": True, "message": "企微连接正常", "access_token": data.get("access_token", "")[:20] + "..."}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 飞书配置 ====================

@router.post("/feishu/save", response_model=dict)
async def save_feishu_config(input: FeishuConfigInput):
    """保存飞书配置"""
    try:
        result = db.save_feishu_config(
            app_id=input.app_id,
            app_secret=input.app_secret,
            verify_token=input.verify_token,
            is_active=input.is_active
        )
        return {"success": True, "message": "飞书配置已保存"}
    except Exception as e:
        raise HTTPException(500, f"保存配置失败: {str(e)}")


@router.get("/feishu/", response_model=dict)
async def get_feishu_config():
    """获取飞书配置"""
    config = db.get_feishu_config()
    return {"configured": bool(config.get("app_secret")), "data": config}


@router.post("/feishu/test")
async def test_feishu_connection():
    """测试飞书连接"""
    config = db.get_feishu_config()
    if not config.get("app_secret"):
        raise HTTPException(400, "请先配置飞书 App Secret")
    
    try:
        import aiohttp
        # 获取 tenant_access_token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        payload = {"app_id": config["app_id"], "app_secret": config["app_secret"]}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                data = await resp.json()
                if data.get("code", -1) != 0:
                    return {"success": False, "error": data.get("msg", "未知错误")}
                return {"success": True, "message": "飞书连接正常", "token": data.get("tenant_access_token", "")[:20] + "..."}
    except Exception as e:
        return {"success": False, "error": str(e)}
