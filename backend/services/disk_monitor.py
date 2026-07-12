"""
磁盘空间监控服务 — 检测U盘/存储设备剩余空间
用于防止照片和数据库增长填满U盘导致系统崩溃
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List
import datetime


def get_disk_usage(path: str) -> Dict[str, Any]:
    """获取指定路径的磁盘使用情况
    
    Returns:
        {
            "total_bytes": int,
            "used_bytes": int,
            "free_bytes": int,
            "usage_percent": float,  # 0-100
            "warning_threshold": 85,  # 超过此值触发警告
            "critical_threshold": 95,  # 超过此值触发严重告警
            "status": "ok" | "warning" | "critical"
        }
    """
    try:
        total, used, free = shutil.disk_usage(path)
        usage_pct = (used / total) * 100 if total > 0 else 0
        
        if usage_pct >= 95:
            status = "critical"
        elif usage_pct >= 85:
            status = "warning"
        else:
            status = "ok"
        
        return {
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "usage_percent": round(usage_pct, 1),
            "warning_threshold": 85,
            "critical_threshold": 95,
            "status": status,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except OSError as e:
        return {
            "error": str(e),
            "status": "unknown"
        }


def get_photo_storage_stats(data_dir: str) -> Dict[str, Any]:
    """获取照片目录存储统计
    
    Args:
        data_dir: 数据目录路径
        
    Returns:
        {
            "total_photos": int,
            "total_size_bytes": int,
            "total_size_mb": float,
            "largest_photo": {"filename": str, "size": int},
            "recent_7_days_count": int,
            "oldest_photo_age_days": int
        }
    """
    photo_dir = Path(data_dir) / "photos"
    
    result = {
        "total_photos": 0,
        "total_size_bytes": 0,
        "total_size_mb": 0.0,
        "largest_photo": None,
        "recent_7_days_count": 0,
        "oldest_photo_age_days": 0
    }
    
    if not photo_dir.exists():
        return result
    
    now = datetime.datetime.now()
    week_ago = now - datetime.timedelta(days=7)
    
    largest_size = 0
    largest_name = ""
    oldest_mtime = float('inf')
    
    for f in photo_dir.iterdir():
        if f.is_file():
            size = f.stat().st_size
            mtime = f.stat().st_mtime
            age_days = (now.timestamp() - mtime) / 86400
            
            result["total_photos"] += 1
            result["total_size_bytes"] += size
            
            if size > largest_size:
                largest_size = size
                largest_name = f.name
            
            if mtime < oldest_mtime:
                oldest_mtime = mtime
            
            if datetime.datetime.fromtimestamp(mtime) >= week_ago:
                result["recent_7_days_count"] += 1
    
    result["total_size_mb"] = round(result["total_size_bytes"] / (1024**2), 2)
    
    if largest_name:
        result["largest_photo"] = {
            "filename": largest_name,
            "size_bytes": largest_size,
            "size_mb": round(largest_size / (1024**2), 2)
        }
    
    if oldest_mtime != float('inf'):
        result["oldest_photo_age_days"] = int((now.timestamp() - oldest_mtime) / 86400)
    
    return result


def get_database_size(data_dir: str) -> Dict[str, Any]:
    """获取数据库文件大小
    
    Returns:
        {"db_path": str, "size_bytes": int, "size_mb": float}
    """
    db_path = Path(data_dir) / "move_hermes.db"
    
    if db_path.exists():
        size = db_path.stat().st_size
        return {
            "db_path": str(db_path),
            "size_bytes": size,
            "size_mb": round(size / (1024**2), 2)
        }
    
    return {
        "db_path": str(db_path),
        "size_bytes": 0,
        "size_mb": 0.0,
        "exists": False
    }


def get_storage_overview(data_dir: str) -> Dict[str, Any]:
    """获取完整的存储概览（磁盘 + 照片 + 数据库）
    
    This is the main API endpoint data structure.
    """
    disk_info = get_disk_usage(data_dir)
    photo_stats = get_photo_storage_stats(data_dir)
    db_info = get_database_size(data_dir)
    
    # 计算总存储使用
    total_data_size = photo_stats["total_size_bytes"] + db_info["size_bytes"]
    
    overview = {
        "disk": disk_info,
        "photos": photo_stats,
        "database": db_info,
        "total_data_size_mb": round(total_data_size / (1024**2), 2),
        "recommendations": []
    }
    
    # 生成建议
    if disk_info.get("status") == "critical":
        overview["recommendations"].append({
            "level": "critical",
            "message": "⚠️ 存储空间即将耗尽！请立即清理旧照片或更换U盘",
            "action": "delete_old_photos"
        })
    elif disk_info.get("status") == "warning":
        overview["recommendations"].append({
            "level": "warning",
            "message": "⚡ 存储空间不足85%，建议定期清理旧照片",
            "action": "review_photos"
        })
    
    if photo_stats["recent_7_days_count"] > 100:
        overview["recommendations"].append({
            "level": "info",
            "message": f"最近7天上传了{photo_stats['recent_7_days_count']}张照片，注意控制频率",
            "action": "none"
        })
    
    return overview


def cleanup_old_photos(data_dir: str, keep_recent_days: int = 30, max_total_size_mb: int = 500) -> Dict[str, Any]:
    """清理旧照片以释放空间
    
    Args:
        data_dir: 数据目录
        keep_recent_days: 保留最近N天的照片
        max_total_size_mb: 照片目录最大总大小(MB)
        
    Returns:
        {"deleted_count": int, "freed_bytes": int, "remaining_photos": int}
    """
    photo_dir = Path(data_dir) / "photos"
    if not photo_dir.exists():
        return {"deleted_count": 0, "freed_bytes": 0, "remaining_photos": 0}
    
    now = datetime.datetime.now()
    cutoff_date = now - datetime.timedelta(days=keep_recent_days)
    
    deleted_count = 0
    freed_bytes = 0
    remaining_photos = []
    
    for f in photo_dir.iterdir():
        if f.is_file():
            mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff_date:
                try:
                    freed_bytes += f.stat().st_size
                    f.unlink()
                    deleted_count += 1
                except Exception:
                    pass
            else:
                remaining_photos.append(f.name)
    
    return {
        "deleted_count": deleted_count,
        "freed_bytes": freed_bytes,
        "freed_mb": round(freed_bytes / (1024**2), 2),
        "remaining_photos": len(remaining_photos),
        "cutoff_date": cutoff_date.isoformat()
    }
