"""
AI 服务 — 照片识别与订单提取
支持多提供商：OpenAI / Azure / Claude / 智谱 / 阿里云 / DeepSeek / Moonshot / 百川 / MiniMax / Ollama / 自定义
"""
import json
import re
import os
import base64
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from pathlib import Path


# 尝试导入本地 OCR
try:
    from ocr_service import parse_order_from_text, parse_production_from_text
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


class AIService:
    """AI 服务封装 — 统一多提供商接口"""
    
    # 各提供商的 Claude 兼容 API 路径
    CLAUDE_COMPAT_URLS = {
        "claude": "https://api.anthropic.com/v1/messages",
        "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1/messages",
    }
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.provider = config.get("provider", "openai")
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "gpt-4o-mini")
        self.base_url = config.get("base_url", self._default_base_url())
    
    def _default_base_url(self) -> str:
        defaults = {
            "openai": "https://api.openai.com/v1",
            "azure": "https://{}.openai.azure.com".format(os.environ.get("AZURE_DEPLOYMENT_NAME", "openai")),
            "claude": "https://api.anthropic.com/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "moonshot": "https://api.moonshot.cn/v1",
            "baichuan": "https://api.baichuan-ai.com/v1",
            "minimax": "https://api.minimax.chat/v1",
            "ollama": "http://localhost:11434/v1",
        }
        return defaults.get(self.provider, "https://api.openai.com/v1")
    
    def _is_claude_api(self) -> bool:
        """判断是否为 Claude API（需要不同请求格式）"""
        return self.provider == "claude"
    
    def _build_messages(self, system_prompt: str, user_text: str, image_b64: Optional[str] = None) -> list:
        """构建消息列表，兼容不同 API 格式"""
        if self._is_claude_api() and image_b64:
            # Claude API 格式
            content_parts = [{"type": "text", "text": user_text}]
            if image_b64:
                content_parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_b64
                    }
                })
            return {
                "system": system_prompt,
                "messages": [{"role": "user", "content": content_parts}]
            }
        else:
            # OpenAI 兼容格式
            content = [{"type": "text", "text": user_text}]
            if image_b64:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_b64}",
                        "detail": "high"
                    }
                })
            return {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ]
            }
    
    def _build_url(self, path: str = "/chat/completions") -> str:
        """构建 API 请求 URL"""
        base = self.base_url.rstrip("/")
        
        # Azure 特殊处理
        if self.provider == "azure":
            api_version = "2024-06-01"
            deployment = self.model  # Azure 用 deployment name
            return f"{base}/{deployment}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        
        # Anthropic API 不用 /chat/completions
        if self._is_claude_api():
            return base + "/messages"
        
        return base + path
    
    def _build_headers(self) -> dict:
        """构建请求头"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Anthropic 特殊头
        if self._is_claude_api():
            headers["anthropic-version"] = "2023-06-01"
        
        # MiniMax 特殊头
        if self.provider == "minimax":
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    def _build_payload(self, system_prompt: str, user_text: str, 
                       image_b64: Optional[str] = None, is_json: bool = True) -> dict:
        """构建请求体"""
        msg_data = self._build_messages(system_prompt, user_text, image_b64)
        
        if self._is_claude_api():
            payload = {
                "model": self.model,
                "max_tokens": 4096,
                **msg_data
            }
        else:
            payload = {
                "model": self.model,
                "messages": msg_data["messages"],
                "temperature": 0.1
            }
            if is_json:
                payload["response_format"] = {"type": "json_object"}
        
        return payload
    
    async def _parse_response(self, data: dict) -> Dict[str, Any]:
        """解析 API 响应，统一输出格式"""
        if self._is_claude_api():
            # Claude API 响应格式
            content_blocks = data.get("content", [])
            text = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    text += block.get("text", "")
        else:
            # OpenAI 兼容格式
            content = data["choices"][0]["message"]["content"]
            text = content
        
        try:
            result = json.loads(text)
            # 添加置信度
            fields = len([k for k in ["order_no", "customer", "product", "quantity", "unit_price", "total_amount", "delivery_date"] if result.get(k)])
            result["confidence"] = min(0.95, fields * 0.15)
            return result
        except (json.JSONDecodeError, KeyError):
            return {"error": "AI 返回格式不正确", "raw": text[:200]}
    
    async def _call_api(self, system_prompt: str, user_text: str,
                       image_b64: Optional[str] = None, is_json: bool = True) -> Dict[str, Any]:
        """通用 API 调用"""
        url = self._build_url()
        headers = self._build_headers()
        payload = self._build_payload(system_prompt, user_text, image_b64, is_json)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, 
                                       timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        # 降级到 OCR
                        if HAS_OCR and image_b64:
                            return await self._fallback_ocr(image_b64, is_production=(system_prompt.find("工序") >= 0))
                        return {"error": f"API 调用失败 ({resp.status}): {error_text[:300]}"}
                    
                    data = await resp.json()
                    return await self._parse_response(data)
        except asyncio.TimeoutError:
            if HAS_OCR and image_b64:
                return await self._fallback_ocr(image_b64, is_production=(system_prompt.find("工序") >= 0))
            return {"error": "请求超时"}
        except Exception as e:
            if HAS_OCR and image_b64:
                return await self._fallback_ocr(image_b64, is_production=(system_prompt.find("工序") >= 0))
            return {"error": str(e)}
    
    async def _call_vision_api(self, system_prompt: str, image_b64: str, 
                               is_production: bool = False) -> Dict[str, Any]:
        """调用多模态大模型 API"""
        user_text = "请识别这张图片中的信息并提取结构化数据。"
        return await self._call_api(system_prompt, user_text, image_b64, is_json=True)
    
    def _order_system_prompt(self) -> str:
        return """你是一个制造业订单识别专家。请从用户上传的订单照片中提取以下信息：
- order_no: 订单编号（字符串，如无则为null）
- customer: 客户名称
- product: 产品名称及规格
- quantity: 数量（数字）
- unit: 单位（件/套/吨/kg等，默认"件"）
- unit_price: 单价（数字，如无则为null）
- total_amount: 总金额（数字，如无则为null）
- delivery_date: 交货日期（YYYY-MM-DD格式，如无则为null）
- priority: 优先级（"urgent"或"normal"）
- notes: 备注/特殊要求

必须返回严格的JSON格式，不要包含任何其他文字。"""
    
    def _production_system_prompt(self) -> str:
        return """你是一个车间工单识别专家。请从工序完成照片中提取：
- task_name: 工序名称（下料/加工/焊接/组装/质检/包装等）
- quantity: 完成数量（数字）
- worker_name: 工人姓名
- date: 完成日期（YYYY-MM-DD格式）
- notes: 备注

必须返回严格的JSON格式，不要包含任何其他文字。"""
    
    async def parse_order_photo(self, image_base64: str) -> Dict[str, Any]:
        """从订单照片中提取结构化数据"""
        return await self._call_vision_api(
            self._order_system_prompt(), image_base64, is_production=False
        )
    
    async def parse_production_photo(self, image_base64: str) -> Dict[str, Any]:
        """从工单照片中提取工序信息"""
        return await self._call_vision_api(
            self._production_system_prompt(), image_base64, is_production=True
        )
    
    async def _fallback_ocr(self, image_b64: str, is_production: bool) -> Dict[str, Any]:
        """降级：使用本地 OCR 识别"""
        import tempfile
        try:
            img_data = base64.b64decode(image_b64)
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(img_data)
                tmp_path = f.name
            
            try:
                from ocr_service import extract_text_from_image
                text = extract_text_from_image(tmp_path)
                if is_production:
                    return parse_production_from_text(text)
                else:
                    return parse_order_from_text(text)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        except Exception:
            return {"error": "OCR 识别失败，请配置 AI API 或安装 tesseract"}
    
    async def test_connection(self) -> Dict[str, Any]:
        """测试 AI 连接"""
        url = self._build_url()
        headers = self._build_headers()
        
        if self._is_claude_api():
            payload = {
                "model": self.model,
                "max_tokens": 10,
                "system": "Reply: OK",
                "messages": [{"role": "user", "content": "OK"}]
            }
        else:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "回复: OK"}],
                "max_tokens": 10
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, 
                                       timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if self._is_claude_api():
                            content_blocks = data.get("content", [])
                            text = ""
                            for block in content_blocks:
                                if block.get("type") == "text":
                                    text += block.get("text", "")
                        else:
                            text = data["choices"][0]["message"]["content"].strip()
                        return {"success": True, "message": "AI 连接正常", "response": text}
                    else:
                        error_text = await resp.text()
                        return {"success": False, "error": f"HTTP {resp.status}: {error_text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
