"""
企微/飞书机器人回调 API
"""
from fastapi import APIRouter, HTTPException, Request, Form, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
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
try:
    from .services.ai_service import AIService
except ImportError:
    _backend = str(Path(__file__).resolve().parent)
    if _backend not in sys.path:
        sys.path.insert(0, _backend)
    from services.ai_service import AIService

router = APIRouter(prefix="/api/webhook", tags=["机器人回调"])


# ==================== 企微回调 ====================

@router.post("/wecom")
async def wecom_callback(request: Request):
    """企业微信机器人回调"""
    try:
        body = await request.json()
    except Exception:
        return {"msg": "ok"}  # 企微要求回调成功响应
    
    # 企微验证token（首次配置时）
    if body.get("encrypt"):
        # 解密逻辑（略，生产环境需要实现）
        return {"msg": "ok"}
    
    # 处理消息事件
    # 企微回调暂用简单处理
    event = body.get("Event", {}) or body
    
    # 处理图片消息
    msgtype = body.get("MsgType", "").lower()
    if msgtype == "image":
        media_id = body.get("Image", {}).get("PicUrl") or body.get("MediaId")
        if not media_id:
            media_id = body.get("MediaId")
        
        if media_id:
            # 异步处理：下载图片 → AI识别 → 更新进度
            asyncio.create_task(_process_wecom_image(media_id, body))
    
    # 处理文本消息
    elif msgtype == "text":
        content = body.get("Text", {}).get("Content", "")
        if content:
            asyncio.create_task(_process_wecom_text(content, body))
    
    return {"msg": "ok"}


async def _process_wecom_image(media_id: str, body: Dict):
    """异步处理企微图片消息"""
    try:
        # 获取用户信息
        userid = body.get("UserId", "")
        
        # TODO: 通过企微API获取access_token并下载图片
        # 这里先模拟流程
        config = db.get_api_config()
        if not config:
            return
        
        ai = AIService({
            "provider": config["provider"],
            "api_key": config["api_key"],
            "model": config["model"],
            "base_url": config.get("base_url")
        })
        
        # 在实际场景中，需要先通过media_id下载图片到本地
        # 然后转为base64传给AI
        # 这里跳过下载步骤，记录日志
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO production_logs (task_id, photo_url, status, worker_name) "
                "VALUES (?, ?, 'pending_review', ?)",
                (None, f"wecom://{media_id}", userid or "unknown")
            )
    except Exception as e:
        print(f"[企微回调] 处理图片失败: {e}")


async def _process_wecom_text(content: str, body: Dict):
    """异步处理企微文本消息"""
    # 支持快捷指令
    if content.strip() == "加急":
        # TODO: 查询最近待处理的订单并标记加急
        pass
    elif content.strip().startswith("订单"):
        # 尝试从文本中提取订单号
        order_no = content.replace("订单", "").strip()
        # 搜索订单...
        pass


# ==================== 飞书回调 ====================

@router.post("/feishu")
async def feishu_callback(request: Request):
    """飞书机器人回调"""
    try:
        body = await request.json()
    except Exception:
        return {"error": "invalid_request"}
    
    # 飞书验证challenge
    challenge = body.get("challenge")
    if challenge:
        return {"challenge": challenge}
    
    # 处理事件
    event = body.get("event", {})
    if not event:
        return {"error": "no_event"}
    
    # 只处理消息接收事件
    if event.get("type") != "im.message.receive_v1":
        return {"error": "ignored"}
    
    message = event.get("message", {})
    msg_type = message.get("message_type", "")
    
    if msg_type == "image":
        # 异步处理
        asyncio.create_task(_process_feishu_image(event))
    
    return {"error": "ignored"}


async def _process_feishu_image(event: Dict):
    """异步处理飞书图片消息"""
    try:
        message = event.get("message", {})
        chat_id = message.get("chat_id", "")
        sender = message.get("sender", {}).get("sender_id", {})
        
        # 获取图片key
        image_key = message.get("content", {})
        if isinstance(image_key, str):
            import json
            try:
                image_key = json.loads(image_key)
            except:
                image_key = {}
        image_key = image_key.get("image_key", "")
        
        # TODO: 通过飞书API下载图片
        # 然后调用AI识别
        
        print(f"[飞书回调] 收到图片: chat={chat_id}, key={image_key}")
    except Exception as e:
        print(f"[飞书回调] 处理图片失败: {e}")


# ==================== 通用消息发送 ====================

class MessageSendRequest(BaseModel):
    """消息发送请求（内部使用）"""
    platform: str  # wecom | feishu
    chat_id: str
    content: str
    msgtype: str = "text"  # text | image


@router.post("/send")
async def send_message(req: MessageSendRequest):
    """
    发送消息到企微/飞书群
    
    注意：这是内部接口，由系统内部调用
    """
    # TODO: 实现消息发送逻辑
    return {"success": True, "message": "消息已发送"}
