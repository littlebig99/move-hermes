"""
AI 服务 — 照片识别与订单提取
"""
import json
import aiohttp
from typing import Optional, Dict, Any

class AIService:
    """AI 服务封装"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.provider = config.get("provider", "openai")
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "gpt-4o-mini")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
    
    async def parse_order_photo(self, image_base64: str) -> Dict[str, Any]:
        """
        从订单照片中提取结构化数据
        
        Args:
            image_base64: Base64编码的图片
            
        Returns:
            提取的订单信息字典
        """
        # 构建系统提示词
        system_prompt = """你是一个制造业订单识别专家。请从用户上传的订单照片中提取以下信息：
- 订单编号（如果有）
- 客户名称
- 产品名称及规格
- 数量
- 单位（件/套/吨等）
- 单价（如果有）
- 交货日期
- 备注/特殊要求
- 优先级（加急/普通）

返回JSON格式，如果某个字段无法识别，设为null。"""
        
        # 构建用户消息
        user_message = {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        }
        
        # 调用AI API
        return await self._call_llm(system_prompt, user_message)
    
    async def parse_production_photo(self, image_base64: str) -> Dict[str, Any]:
        """
        从工单照片中提取工序完成信息
        
        Returns:
            工序信息字典（工序名称、完成数量、工人姓名等）
        """
        system_prompt = """你是一个车间工单识别专家。请从用户上传的工序完成照片中提取：
- 工序名称（下料/加工/焊接/组装/质检/包装等）
- 完成数量
- 完成时间
- 工人姓名（如果有签名或工牌）
- 备注

返回JSON格式。"""
        
        user_message = {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
        }
        
        return await self._call_llm(system_prompt, user_message)
    
    async def _call_llm(self, system_prompt: str, user_message: Dict) -> Dict[str, Any]:
        """
        调用大模型API
        
        根据配置选择不同的API端点和请求格式
        """
        # 这里需要根据实际provider实现不同的请求格式
        # 目前以OpenAI格式为例
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [user_message]}
            ],
            "response_format": {"type": "json_object"}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    return {"error": f"API调用失败: {resp.status}"}
                
                data = await resp.json()
                content = data["choices"][0]["message"]["content"]
                
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {"error": "AI返回格式不正确", "raw": content}


# ==================== 企微/飞书适配器 ====================

class WebhookAdapter:
    """
    企微/飞书机器人回调适配器
    
    统一接口，支持多种消息平台
    """
    
    def __init__(self, platform: str = "wecom"):
        self.platform = platform  # wecom | feishu
    
    async def handle_message(self, raw_event: Dict) -> Dict:
        """
        处理 incoming 消息
        
        Args:
            raw_event: 原始事件数据（企微或飞书格式）
            
        Returns:
            处理结果
        """
        if self.platform == "wecom":
            return await self._handle_wecom(raw_event)
        elif self.platform == "feishu":
            return await self._handle_feishu(raw_event)
        else:
            return {"error": "不支持的平台"}
    
    async def _handle_wecom(self, event: Dict) -> Dict:
        """处理企业微信消息"""
        msg_type = event.get("msgtype", "")
        
        if msg_type == "image":
            media_id = event.get("image", {}).get("pic_url", "")
            # 下载图片 → AI识别 → 更新订单
            return {"type": "image_processing", "media_id": media_id}
        
        elif msg_type == "text":
            content = event.get("text", {}).get("content", "")
            return {"type": "text_processing", "content": content}
        
        return {"type": "unsupported"}
    
    async def _handle_feishu(self, event: Dict) -> Dict:
        """处理飞书消息"""
        # 类似企微，但使用飞书的事件格式
        msg_type = event.get("message", {}).get("message_type", "")
        
        if msg_type == "image":
            return {"type": "image_processing"}
        
        return {"type": "unsupported"}
