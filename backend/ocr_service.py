"""
本地 OCR 识别 — 无需 API Key
使用 pytesseract + PIL 实现基础文字识别
"""
import json
import re
import os
from typing import Optional, Dict, Any

try:
    import pytesseract
    from PIL import Image
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


def extract_text_from_image(image_path: str) -> str:
    """从图片中提取文字（OCR）"""
    if not HAS_TESSERACT:
        return ""
    try:
        img = Image.open(image_path)
        # 同时识别中文和英文
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        return text.strip()
    except Exception:
        return ""


def parse_order_from_text(text: str) -> Dict[str, Any]:
    """从OCR文字中提取订单信息"""
    result = {
        "order_no": None,
        "customer": None,
        "product": None,
        "quantity": None,
        "unit_price": None,
        "total_amount": None,
        "delivery_date": None,
        "priority": "normal",
        "notes": None,
        "confidence": 0.0,
        "raw_text": text
    }
    
    if not text:
        return result
    
    # 订单编号
    patterns = [
        r'(?:订单编号|单号|NO\.?|订单号)[:：\s]*(\w[\w\-]{3,})',
        r'(\w[\w\-]{5,})\s*(?:订单|ORDER)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            result["order_no"] = m.group(1)
            break
    
    # 客户名称
    m = re.search(r'(?:客户|买方|采购方)[:：\s]*(.+?)(?:\n|$)', text)
    if m:
        result["customer"] = m.group(1).strip()
    
    # 产品名称
    m = re.search(r'(?:产品|品名|货物|物料)[:：\s]*(.+?)(?:\n|$)', text)
    if m:
        result["product"] = m.group(1).strip()
    
    # 数量
    m = re.search(r'(?:数量|Qty\.?|量)[:：\s]*(\d+\.?\d*)', text)
    if m:
        result["quantity"] = float(m.group(1))
    
    # 单价
    m = re.search(r'(?:单价|价格|Price)[:：\s]*([\d,]+\.\d+|[\d,]+)', text)
    if m:
        result["unit_price"] = float(m.group(1).replace(',', ''))
    
    # 总价
    m = re.search(r'(?:总价|金额|合计|Total)[:：\s]*([\d,]+\.\d+|[\d,]+)', text)
    if m:
        result["total_amount"] = float(m.group(1).replace(',', ''))
    
    # 交货日期
    m = re.search(r'(?:交货|交期|交付|Delivery)[:：\s]*(\d{4}[年\-]\d{1,2}[月\-]\d{1,2}|\d{4}-\d{2}-\d{2})', text)
    if m:
        result["delivery_date"] = m.group(1).replace('年', '-').replace('月', '-').replace('日', '')
    
    # 优先级
    if re.search(r'(?:加急|紧急|URGENT)', text, re.IGNORECASE):
        result["priority"] = "urgent"
    
    # 单位
    m = re.search(r'(?:单位|Unit)[:：\s]*(件|套|吨|kg|个|箱|支|根|米|块)', text)
    if m:
        result["unit"] = m.group(1)
    
    # 置信度估算
    fields_found = sum(1 for k in ["order_no", "customer", "product", "quantity"] if result[k])
    result["confidence"] = min(0.95, fields_found * 0.25)
    
    return result


def parse_production_from_text(text: str) -> Dict[str, Any]:
    """从OCR文字中提取工序信息"""
    result = {
        "task_name": None,
        "quantity": None,
        "worker_name": None,
        "date": None,
        "notes": None,
        "confidence": 0.0,
        "raw_text": text
    }
    
    if not text:
        return result
    
    # 工序名称
    task_keywords = ['下料', '加工', '车削', '铣削', '磨削', '钻孔', '焊接', '切割',
                     '组装', '装配', '质检', '检验', '包装', '入库', '发货']
    for kw in task_keywords:
        if kw in text:
            result["task_name"] = kw
            break
    
    # 数量
    m = re.search(r'(?:数量|完成|产量|Qty)[:：\s]*(\d+\.?\d*)', text)
    if m:
        result["quantity"] = float(m.group(1))
    
    # 工人姓名
    m = re.search(r'(?:工人|操作员|签字|签名|操作人)[:：\s]*(\S{2,4})', text)
    if m:
        result["worker_name"] = m.group(1).strip()
    
    # 日期
    m = re.search(r'(\d{4}[年\-]\d{1,2}[月\-]\d{1,2}日?)', text)
    if m:
        result["date"] = m.group(1).replace('年', '-').replace('月', '-').replace('日', '')
    
    fields_found = sum(1 for k in ["task_name", "quantity"] if result[k])
    result["confidence"] = min(0.9, fields_found * 0.45)
    
    return result
