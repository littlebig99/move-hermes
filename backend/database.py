"""Move Hermes — 数据库统一入口

拆分自原 database.py（1010行），职责分离为：
- models.py: Pydantic 模型 + 枚举
- connection.py: 线程安全的连接管理
- migration.py: 数据库初始化 + 迁移
- repositories/: 按领域划分的 CRUD 操作

所有原始函数仍可通过本模块直接导入，保持向后兼容。
"""
import sys
from pathlib import Path

# 兼容直接运行和包导入
try:
    from .connection import get_db_path, set_db_path, _resolve_db_path, get_connection
    from .migration import init_db, _migrate_db, get_overdue_orders, get_upcoming_delivery
    from .repositories.order_repo import (
        generate_order_no, create_order, list_orders, get_order,
        update_order, delete_order, mark_urgent,
        _build_safe_where, _ALLOWED_ORDER_COLUMNS
    )
    from .repositories.task_repo import (
        add_task, update_task_status, delete_task,
        get_order_tasks, get_stalled_tasks
    )
    from .repositories.customer_repo import (
        list_customers, create_customer, update_customer,
        get_customer, delete_customer
    )
    from .repositories.product_repo import (
        list_products, create_product, update_product,
        get_product, delete_product
    )
    from .repositories.config_repo import (
        get_api_config, save_api_config,
        get_wecom_config, save_wecom_config,
        get_feishu_config, save_feishu_config,
        check_any_configured
    )
    from .repositories.dashboard_repo import (
        get_dashboard_stats, get_dashboard_production
    )
    from .repositories.production_repo import (
        list_production_logs, confirm_production_log, reject_production_log
    )
except ImportError:
    # 直接运行时（python backend/main.py）的 fallback
    _backend = str(Path(__file__).resolve().parent)
    if _backend not in sys.path:
        sys.path.insert(0, _backend)
    _parent = str(Path(_backend).parent)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)
    
    from connection import get_db_path, set_db_path, _resolve_db_path, get_connection
    from migration import init_db, _migrate_db, get_overdue_orders, get_upcoming_delivery
    from repositories.order_repo import (
        generate_order_no, create_order, list_orders, get_order,
        update_order, delete_order, mark_urgent,
        _build_safe_where, _ALLOWED_ORDER_COLUMNS
    )
    from repositories.task_repo import (
        add_task, update_task_status, delete_task,
        get_order_tasks, get_stalled_tasks
    )
    from repositories.customer_repo import (
        list_customers, create_customer, update_customer,
        get_customer, delete_customer
    )
    from repositories.product_repo import (
        list_products, create_product, update_product,
        get_product, delete_product
    )
    from repositories.config_repo import (
        get_api_config, save_api_config,
        get_wecom_config, save_wecom_config,
        get_feishu_config, save_feishu_config,
        check_any_configured
    )
    from repositories.dashboard_repo import (
        get_dashboard_stats, get_dashboard_production
    )
    from repositories.production_repo import (
        list_production_logs, confirm_production_log, reject_production_log
    )

# 工具函数（旧代码可能直接调用）
def _row_to_dict(row):
    """将sqlite3.Row转为字典"""
    if row is None:
        return None
    return dict(row)


__all__ = [
    # 连接管理
    "get_db_path", "set_db_path", "_resolve_db_path", "get_connection",
    # 初始化
    "init_db", "_migrate_db", "get_overdue_orders", "get_upcoming_delivery",
    # 订单
    "generate_order_no", "create_order", "list_orders", "get_order",
    "update_order", "delete_order", "mark_urgent",
    # 工序
    "add_task", "update_task_status", "delete_task",
    "get_order_tasks", "get_stalled_tasks",
    # 客户
    "list_customers", "create_customer", "update_customer",
    "get_customer", "delete_customer",
    # 产品
    "list_products", "create_product", "update_product",
    "get_product", "delete_product",
    # 配置
    "get_api_config", "save_api_config",
    "get_wecom_config", "save_wecom_config",
    "get_feishu_config", "save_feishu_config",
    "check_any_configured",
    # 看板
    "get_dashboard_stats", "get_dashboard_production",
    # 生产日志
    "list_production_logs", "confirm_production_log", "reject_production_log",
]
