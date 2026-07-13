"""Move Hermes — 配置管理仓库（CRUD）"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# 兼容直接运行和包导入
try:
    from ..connection import get_connection
except ImportError:
    _parent = str(Path(__file__).resolve().parent.parent)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)
    from connection import get_connection


def _row_to_dict(row) -> Dict[str, Any]:
    if row is None:
        return None
    return dict(row)


def get_api_config(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """获取AI API配置"""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM api_config WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        if not row:
            return None
        result = _row_to_dict(row)
        result["api_key"] = "***"
        return result


def save_api_config(provider: str, api_key: str, model: str = "gpt-4o-mini",
                    base_url: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """保存AI API配置"""
    with get_connection(db_path) as conn:
        conn.execute("UPDATE api_config SET is_active = 0")
        cursor = conn.execute(
            "INSERT INTO api_config (provider, api_key, model, base_url, is_active) VALUES (?, ?, ?, ?, 1)",
            (provider, api_key, model, base_url)
        )
        config = conn.execute(
            "SELECT * FROM api_config WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        result = _row_to_dict(config)
        result["api_key"] = "***"
        return result


def get_wecom_config(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """获取企业微信配置"""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM wecom_config WHERE id = 1"
        ).fetchone()
        if not row:
            return {"corp_id": "", "agent_id": "", "secret": "", "webhook_url": "", "is_active": 0}
        return _row_to_dict(row)


def save_wecom_config(corp_id: str, agent_id: str, secret: str,
                      webhook_url: str, is_active: int = 0, db_path: Optional[str] = None) -> Dict[str, Any]:
    """保存企业微信配置"""
    with get_connection(db_path) as conn:
        existing = conn.execute("SELECT id FROM wecom_config WHERE id = 1").fetchone()
        if existing:
            conn.execute(
                "UPDATE wecom_config SET corp_id=?, agent_id=?, secret=?, webhook_url=?, is_active=? WHERE id=1",
                (corp_id, agent_id, secret, webhook_url, is_active)
            )
        else:
            conn.execute(
                "INSERT INTO wecom_config (id, corp_id, agent_id, secret, webhook_url, is_active) VALUES (1, ?, ?, ?, ?, ?)",
                (corp_id, agent_id, secret, webhook_url, is_active)
            )
        return get_wecom_config(db_path)


def get_feishu_config(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """获取飞书配置"""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM feishu_config WHERE id = 1"
        ).fetchone()
        if not row:
            return {"app_id": "", "app_secret": "", "verify_token": "", "is_active": 0}
        return _row_to_dict(row)


def save_feishu_config(app_id: str, app_secret: str, verify_token: str,
                       is_active: int = 0, db_path: Optional[str] = None) -> Dict[str, Any]:
    """保存飞书配置"""
    with get_connection(db_path) as conn:
        existing = conn.execute("SELECT id FROM feishu_config WHERE id = 1").fetchone()
        if existing:
            conn.execute(
                "UPDATE feishu_config SET app_id=?, app_secret=?, verify_token=?, is_active=? WHERE id=1",
                (app_id, app_secret, verify_token, is_active)
            )
        else:
            conn.execute(
                "INSERT INTO feishu_config (id, app_id, app_secret, verify_token, is_active) VALUES (1, ?, ?, ?, ?)",
                (app_id, app_secret, verify_token, is_active)
            )
        return get_feishu_config(db_path)


def check_any_configured(db_path: Optional[str] = None) -> Dict[str, bool]:
    """检查各项配置是否已配置"""
    with get_connection(db_path) as conn:
        api = conn.execute("SELECT COUNT(*) FROM api_config WHERE is_active=1 AND api_key!=''").fetchone()[0]
        wecom = conn.execute("SELECT COUNT(*) FROM wecom_config WHERE is_active=1").fetchone()[0]
        feishu = conn.execute("SELECT COUNT(*) FROM feishu_config WHERE is_active=1").fetchone()[0]
        return {
            "ai_configured": api > 0,
            "wecom_configured": wecom > 0,
            "feishu_configured": feishu > 0,
            "any_configured": api > 0 or wecom > 0 or feishu > 0
        }
