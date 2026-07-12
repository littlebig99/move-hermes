"""
Move Hermes — 后端API集成测试
运行: cd backend && python test_api.py
"""
import sqlite3
import json
import sys
from pathlib import Path

# 使用测试数据库
TEST_DB = str(Path(__file__).parent / "test_move_hermes.db")

# 临时修改database.py的DB_PATH
import database as db
db._resolve_db_path(TEST_DB)

# 清理旧测试库
if Path(TEST_DB).exists():
    Path(TEST_DB).unlink()

print("=" * 60)
print("  Move Hermes API 集成测试")
print("=" * 60)

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))
        failed += 1


# ========== 测试1: 数据库初始化 ==========
print("\n【1】数据库初始化")
db.init_db(TEST_DB)
test("数据库文件创建", Path(TEST_DB).exists())

conn = sqlite3.connect(TEST_DB)
tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
expected_tables = ["customers", "products", "orders", "order_tasks",
                   "production_logs", "api_config", "wecom_config", "feishu_config"]
test("所有表已创建", all(t in tables for t in expected_tables),
     f"缺少: {[t for t in expected_tables if t not in tables]}")
conn.close()

# ========== 测试2: 客户管理 ==========
print("\n【2】客户管理")

# 创建客户
customer = db.create_customer("张三贸易公司", "张三", "13800138000", "上海市浦东新区")
test("创建客户", customer is not None and customer["id"] > 0, f"返回: {customer}")
customer_id = customer["id"]

# 获取客户
c = db.get_customer(customer_id)
test("获取客户", c is not None and c["name"] == "张三贸易公司")

# 更新客户
updated = db.update_customer(customer_id, {"phone": "13900139000"})
test("更新客户", updated and updated["phone"] == "13900139000")

# 列表
result = db.list_customers()
test("客户列表", len(result["customers"]) >= 1 and result["total"] >= 1)

# 删除客户
test("删除客户", db.delete_customer(customer_id))
test("删除后列表为空", db.list_customers()["total"] == 0)

# ========== 测试3: 产品管理 ==========
print("\n【3】产品管理")

product = db.create_product("不锈钢法兰", "DN50 PN16", "件", "管道配件")
test("创建产品", product is not None and product["id"] > 0)
product_id = product["id"]

p = db.get_product(product_id)
test("获取产品", p is not None and p["name"] == "不锈钢法兰")

result = db.list_products()
test("产品列表", len(result["products"]) >= 1)

db.delete_product(product_id)
test("删除产品", db.list_products()["total"] == 0)

# ========== 测试4: 订单管理 ==========
print("\n【4】订单管理")

# 准备客户和产品
cust = db.create_customer("测试客户A", "测试", "13800000001")
prod = db.create_product("测试产品X", "规格A", "件", "测试")

# 创建订单
order = db.create_order(
    customer_id=cust["id"],
    product_id=prod["id"],
    quantity=500,
    unit_price=2.5,
    priority="normal"
)
test("创建订单", order is not None and "order_no" in order)
order_id = order["id"]
order_no = order["order_no"]
test("订单号格式", order_no.startswith("ORD-"))
test("总金额计算", abs(order.get("total_amount", 0) - 1250.0) < 0.01)

# 验证默认工序
tasks = db.get_order_tasks(order_id)
test("默认工序创建", len(tasks) == 6)
task_names = [t["task_name"] for t in tasks]
expected_tasks = ["下料", "加工", "组装", "质检", "包装", "发货"]
test("工序名称正确", task_names == expected_tasks)

# 获取订单详情
detail = db.get_order(order_id)
test("订单详情", detail is not None and "tasks" in detail)

# 更新订单
updated = db.update_order(order_id, {"priority": "urgent", "notes": "加急处理"})
test("更新订单", updated and updated["priority"] == "urgent" and updated["notes"] == "加急处理")

# 标记加急（另一种方式）
urgent = db.mark_urgent(order_id)
test("标记加急", urgent and urgent["priority"] == "urgent")

# 列表
result = db.list_orders()
test("订单列表", len(result["orders"]) >= 1)

# 按状态筛选
result = db.list_orders(status="pending")
test("按状态筛选", all(o["status"] == "pending" for o in result["orders"]))

# 按优先级筛选
result = db.list_orders(priority="urgent")
test("按优先级筛选", all(o["priority"] == "urgent" for o in result["orders"]))

# ========== 测试5: 工序管理 ==========
print("\n【5】工序管理")

# 更新工序状态（进行中）
task = tasks[0]  # 第一道工序
updated_task = db.update_task_status(
    task_id=task["id"],
    status="in_progress",
    worker_name="李师傅"
)
test("工序→进行中", updated_task and updated_task["status"] == "in_progress")

# 更新工序状态（完成）
completed_task = db.update_task_status(
    task_id=task["id"],
    status="completed",
    worker_name="李师傅",
    ai_confidence=0.95,
    ai_notes="下料完成，数量500件"
)
test("工序→已完成", completed_task and completed_task["status"] == "completed")
test("AI置信度记录", completed_task and abs(completed_task.get("ai_confidence", 0) - 0.95) < 0.01)

# 获取下一道工序
next_task_id = completed_task.get("next_task")
test("自动推进到下一道", next_task_id is not None)
if next_task_id:
    test("下一道工序名称", next_task_id["task_name"] == "加工")

# 呆滞检测
stalled = db.get_stalled_tasks(0)  # 阈值0天，应该能查到
test("呆滞检测", isinstance(stalled, list))

# ========== 测试6: 看板数据 ==========
print("\n【6】看板数据")

stats = db.get_dashboard_stats()
test("看板统计", "in_production" in stats and "urgent" in stats)
test("进行中数量", stats.get("in_production", 0) >= 1)
test("加急数量", stats.get("urgent", 0) >= 1)

production = db.get_dashboard_production()
test("生产看板", len(production) >= 1)
if production:
    order_data = production[0]
    test("看板含工序信息", "tasks" in order_data and len(order_data["tasks"]) > 0)

# ========== 测试7: 逾期预警 ==========
print("\n【7】预警")

# 创建一个已过期的订单
import datetime
past_date = (datetime.date.today() - datetime.timedelta(days=5)).isoformat()
old_order = db.create_order(
    customer_id=cust["id"],
    product_id=prod["id"],
    quantity=100,
    delivery_date=past_date,
    order_no="ORD-TEST-EXPIRED"
)
overdue = db.get_overdue_orders()
test("逾期订单检测", len(overdue) >= 1)

upcoming = db.get_upcoming_delivery(30)
test("即将到期检测", isinstance(upcoming, list))

# ========== 测试8: API配置 ==========
print("\n【8】API配置")

config = db.save_api_config("openai", "sk-test-key-12345", "gpt-4o-mini", "https://api.openai.com/v1")
test("保存配置", config is not None)
test("API Key隐藏", config.get("api_key") == "***")

retrieved = db.get_api_config()
test("读取配置", retrieved is not None and retrieved["provider"] == "openai")

# ========== 测试9: 生产日志 ==========
print("\n【9】生产日志")

# 获取当前工序
current_tasks = db.get_order_tasks(order_id)
in_progress_task = [t for t in current_tasks if t["status"] == "in_progress"]
if in_progress_task:
    task_id = in_progress_task[0]["id"]
    logs = db.list_production_logs(task_id=task_id)
    test("生产日志查询", isinstance(logs, dict))
else:
    print("  ⚠️  跳过生产日志测试（无进行中工序）")

# ========== 清理 ==========
print("\n" + "=" * 60)
print(f"  测试结果: {passed} 通过, {failed} 失败, 共 {passed + failed} 项")
print("=" * 60)

# 清理测试文件
try:
    Path(TEST_DB).unlink()
except:
    pass

sys.exit(0 if failed == 0 else 1)
