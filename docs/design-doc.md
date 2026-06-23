# Move Hermes — 设计文档 v1.0

> 生成日期: 2026-06-23
> 项目路径: E:\project\move-hermes
> MVP范围: 订单跟踪 Agent
> 商业模式: 一次性卖断 + 后续功能开发/个性化定制收费

---

## 1. 产品定位

**Move Hermes** 是一款面向20人以下小型制造/加工企业的U盘智能体系统。

核心价值：让小企业用最低的成本（一个U盘 + 一次配置），获得一套AI驱动的订单管理系统。

**差异化优势：**
- 即插即用：U盘预装，双击启动，无需安装
- AI优先：从照片/聊天中自动提取结构化数据，减少人工录入
- 数据随身：SQLite数据库存在U盘上，换电脑不换数据
- 渐进式扩展：MVP做订单跟踪，后续增加财务和仓库模块

---

## 2. MVP范围：订单跟踪 Agent

### 2.1 核心用户角色

| 角色 | 人数 | 使用频率 | 主要功能 |
|------|------|----------|----------|
| 老板/管理员 | 1-2人 | 每天 | 查看所有订单、生产进度、创建/编辑订单 |
| 文员/跟单员 | 1人 | 每天 | 录入新订单、复核AI识别结果、更新订单状态 |
| 车间工人 | 3-10人 | 每道工序完成后 | 在企微/飞书群拍照上传工单 |

### 2.2 核心业务流程

```
订单创建
    │
    ├── 渠道1: 老板/文员 → 拍照纸质单据 → AI识别 → 人工复核 → 入库
    │
    └── 渠道2: 工人 → 企微/飞书群 → 拍照工单 → AI自动识别 → 自动入库
         │
         ▼
    订单进入生产队列
         │
         ▼
    分配工序（下料 → 加工 → 组装 → 质检 → 包装 → 发货）
         │
         ▼
    工人每完成一道工序 → 拍照上报 → AI识别 → 更新进度
         │
         ▼
    生产完成 → 标记待发库 → 通知发货
         │
         ▼
    发货完成 → 标记已完成 → 触发财务模块（预留接口）
```

### 2.3 关键功能清单（MVP）

| 功能 | 优先级 | 描述 |
|------|--------|------|
| 订单创建 | P0 | 支持拍照识别+手动录入两种方式 |
| 生产工序管理 | P0 | 定义订单的工序流程，支持自定义工序 |
| 进度实时看板 | P0 | 一页看清所有订单在哪道工序 |
| 加急单标识 | P0 | 一键标记加急，看板置顶显示 |
| 呆滞预警 | P0 | 某工序停留超过阈值自动标红 |
| 企微/飞书机器人 | P0 | 接收群内照片，自动识别并更新进度 |
| API配置向导 | P0 | 首次启动引导用户配置AI API Key |
| 订单列表/搜索 | P1 | 按客户、日期、状态筛选 |
| 数据导出 | P1 | 导出CSV/Excel |
| 多用户权限 | P2 | 老板可编辑，工人只看自己的工单 |

---

## 3. 技术架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      U盘智能体                               │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              本地服务层 (Python/FastAPI)              │    │
│  │                                                     │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │ Web API  │  │ 机器人   │  │  文件服务        │  │    │
│  │  │ 网关     │  │ 适配器   │  │  (U盘路径)       │  │    │
│  │  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │    │
│  │       │             │                  │            │    │
│  │  ┌────▼─────────────▼──────────────────▼─────────┐  │    │
│  │  │              业务逻辑层                        │  │    │
│  │  │                                              │  │    │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐   │  │    │
│  │  │  │ 订单管理  │  │ 工序管理  │  │ 客户管理  │   │  │    │
│  │  │  └──────────┘  └──────────┘  └──────────┘   │  │    │
│  │  │  ┌──────────┐  ┌──────────┐                  │  │    │
│  │  │  │ 预警引擎  │  │ OCR服务  │                  │  │    │
│  │  │  └──────────┘  └──────────┘                  │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │                                                     │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │              数据访问层                        │  │    │
│  │  │  ┌──────────────────────────────────────┐    │  │    │
│  │  │  │         SQLite (U盘路径)              │    │  │    │
│  │  │  └──────────────────────────────────────┘    │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              前端层 (静态HTML/CSS/JS)                 │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │ 配置向导  │  │ 订单看板  │  │ 订单管理         │  │    │
│  │  │ (首次)   │  │ (首页)    │  │                  │  │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              外部API层                                │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │ 大模型   │  │ 企微API  │  │ 飞书API          │  │    │
│  │  │ (OCR)   │  │ (机器人)  │  │ (机器人)          │  │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| 后端框架 | FastAPI | 异步、自动API文档、性能好 |
| 数据库 | SQLite (带WAL) | 零配置、便携、U盘友好 |
| 前端 | 原生HTML + Alpine.js + Tailwind CSS | 零构建步骤、轻量 |
| AI OCR | 大模型API（GPT-4o/Claude/通义千问） | 高精度、支持中文 |
| 企微/飞书 | 官方机器人SDK | 稳定、官方支持 |
| 自启动 | Python脚本 + BAT批处理 | 零依赖、跨Windows版本 |
| 配置存储 | JSON文件 | 简单、可版本控制 |

---

## 4. 数据库设计

### 4.1 ER图

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   customer   │     │      order       │     │  product     │
├──────────────┤     ├──────────────────┤     ├──────────────┤
│ id (PK)      │──┐  │ id (PK)          │  ┌──│ id (PK)      │
│ name         │  │  │ customer_id (FK) │  │  │ name         │
│ contact      │  │  │ product_id (FK)  │  │  │ spec         │
│ phone        │  │  │ quantity         │  │  │ unit         │
│ created_at   │  │  │ unit_price       │  │  │ category     │
└──────────────┘  │  │ total_amount     │  │  │ created_at   │
                  │  │ status           │  └──────────────┘
                  │  │ priority (normal │
                  │  │   urgent)        │
                  │  │ notes            │
                  │  │ created_at       │
                  │  │ updated_at       │
                  │  └────────┬─────────┘
                  │           │
                  │     ┌─────▼──────────┐
                  │     │   order_task   │
                  │     ├────────────────┤
                  │     │ id (PK)        │
                  │     │ order_id (FK)  │
                  │     │ task_name      │
                  │     │ sequence_num   │
                  │     │ status         │
                  │     │ worker_id      │
                  │     │ started_at     │
                  │     │ completed_at   │
                  │     │ photo_url      │
                  │     │ ai_confidence  │
                  │     │ notes          │
                  │     └────────────────┘
                  │
            ┌─────▼──────────┐
            │   production_log │
            ├────────────────┤
            │ id (PK)        │
            │ task_id (FK)   │
            │ photo_url      │
            │ ai_extracted   │
            │ status         │
            │ worker_name    │
            │ created_at     │
            └────────────────┘
```

### 4.2 表结构详情

#### customers（客户表）
```sql
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact TEXT,
    phone TEXT,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### products（产品表）
```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    spec TEXT,
    unit TEXT DEFAULT '件',
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### orders（订单表）
```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,          -- 订单编号，如 ORD-20260623-001
    customer_id INTEGER REFERENCES customers(id),
    product_id INTEGER REFERENCES products(id),
    quantity REAL NOT NULL,                  -- 数量
    unit_price REAL,                        -- 单价
    total_amount REAL,                      -- 总金额
    status TEXT DEFAULT 'pending',          -- pending|producing|completed|shipped
    priority TEXT DEFAULT 'normal',         -- normal|urgent
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### order_tasks（订单工序表）
```sql
CREATE TABLE order_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER REFERENCES orders(id),
    task_name TEXT NOT NULL,                -- 工序名称，如"下料"、"加工"
    sequence_num INTEGER NOT NULL,          -- 工序序号
    status TEXT DEFAULT 'pending',          -- pending|in_progress|completed
    worker_id INTEGER,                      -- 负责工人ID
    assigned_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    photo_url TEXT,                         -- 完工照片路径
    ai_confidence REAL,                     -- AI识别置信度
    ai_notes TEXT,                          -- AI提取备注
    is_stalled INTEGER DEFAULT 0,           -- 是否呆滞(1=是)
    stalled_since TIMESTAMP                 -- 呆滞开始时间
);
```

#### production_logs（生产日志表）
```sql
CREATE TABLE production_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES order_tasks(id),
    photo_url TEXT,                         -- 上传的照片
    ai_extracted TEXT,                      -- AI提取的JSON字符串
    status TEXT DEFAULT 'pending_review',   -- pending_review|confirmed|rejected
    worker_name TEXT,                       -- 工人姓名
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### api_config（API配置表）
```sql
CREATE TABLE api_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,                 -- openai|claude|aliyun|custom
    api_key TEXT NOT NULL,                  -- 加密存储
    model TEXT DEFAULT 'gpt-4o-mini',      -- 使用的模型
    base_url TEXT,                          -- 自定义API地址
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### wecom_config（企业微信配置表）
```sql
CREATE TABLE wecom_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    corp_id TEXT,
    agent_id TEXT,
    secret TEXT,
    webhook_url TEXT,
    is_active INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### feishu_config（飞书配置表）
```sql
CREATE TABLE feishu_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id TEXT,
    app_secret TEXT,
    is_active INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. API接口设计

### 5.1 认证

```
所有API端点（除 /health 和 /config 外）需要：
Header: Authorization: Bearer <session_token>
Session由首次配置时建立，存储在本地Cookie中
```

### 5.2 核心API

#### 订单管理

```
POST   /api/orders                    # 创建订单
GET    /api/orders                    # 获取订单列表（支持分页/筛选）
GET    /api/orders/{id}               # 获取订单详情
PUT    /api/orders/{id}               # 更新订单
DELETE /api/orders/{id}               # 删除订单
POST   /api/orders/{id}/urgent        # 标记加急
GET    /api/orders/stats              # 订单统计数据
```

#### 工序管理

```
GET    /api/orders/{id}/tasks         # 获取订单的所有工序
POST   /api/orders/{id}/tasks         # 添加新工序
PUT    /api/tasks/{id}/status         # 更新工序状态
GET    /api/tasks/stalled             # 获取呆滞工序列表
```

#### 照片上传与AI识别

```
POST   /api/photos/upload             # 上传图片
POST   /api/photos/{id}/parse         # 触发AI解析
GET    /api/photos/{id}/result        # 获取解析结果

# AI识别返回格式：
{
  "order_no": "ORD-20260623-001",
  "customer": "张三贸易公司",
  "product": "不锈钢法兰DN50",
  "quantity": 500,
  "unit": "件",
  "delivery_date": "2026-07-01",
  "priority": "urgent",
  "notes": "客户要求带合格证",
  "confidence": 0.92
}
```

#### 看板数据

```
GET    /api/dashboard/overview        # 看板概览数据
GET    /api/dashboard/production      # 生产进度看板
GET    /api/dashboard/alerts          # 预警列表
```

#### 机器人回调

```
POST   /api/webhook/wecom             # 企微机器人回调
POST   /api/webhook/feishu            # 飞书机器人回调
```

---

## 6. AI提示词设计

### 6.1 订单照片识别 Prompt

```
你是一个制造业订单识别专家。请从用户上传的订单照片中提取以下信息：

【必填字段】
- 订单编号（如果有）
- 客户名称
- 产品名称及规格
- 数量
- 单位（件/套/吨等）
- 单价（如果有）
- 交货日期

【可选字段】
- 备注/特殊要求
- 优先级（加急/普通）

【输出格式】
返回JSON，不要包含任何其他文字。如果某个字段无法识别，设为null。

【注意事项】
- 注意区分相似数字（如1和7，0和6）
- 注意单位换算
- 如果有多张订单在同一张照片中，分别列出
- 交货日期可能是"下周"、"月底前"等模糊表述，尝试转换为具体日期
```

### 6.2 工单照片识别 Prompt

```
你是一个车间工单识别专家。请从用户上传的工序完成照片中提取：

- 工序名称（下料/加工/焊接/组装/质检/包装等）
- 完成数量
- 完成时间
- 工人姓名（如果有签名或工牌）
- 备注

返回JSON格式。
```

### 6.3 订单号生成规则

```
格式: ORD-{YYYYMMDD}-{序号}
示例: ORD-20260623-001

每日从001重新开始
如果同一天超过999单，自动进位到 ORD-{YYYYMMDD}-{4位序号}
```

---

## 7. 前端页面设计

### 7.1 页面清单

| 页面 | 路由 | 用途 |
|------|------|------|
| 配置向导 | `/config` | 首次启动，设置API Key和模型 |
| 看板首页 | `/dashboard` | 所有订单的生产进度一览 |
| 订单列表 | `/orders` | 全部订单，支持搜索/筛选 |
| 订单详情 | `/orders/:id` | 单个订单的详细信息和工序 |
| 创建订单 | `/orders/new` | 手动创建或拍照上传 |
| 客户管理 | `/customers` | 客户信息维护 |
| 产品管理 | `/products` | 产品信息维护 |
| 预警中心 | `/alerts` | 呆滞预警、逾期预警 |

### 7.2 看板首页布局

```
┌─────────────────────────────────────────────────────────┐
│  Move Hermes  │  🔔 3个预警  │  👤 管理员               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📊 今日概况                                            │
│  ┌─────────┬─────────┬─────────┬─────────┐             │
│  │ 进行中  │ 待开工  │ 已完成  │ 加急    │             │
│ │  12     │   5     │   8     │   3     │             │
│  └─────────┴─────────┴─────────┴─────────┘             │
│                                                         │
│  🔴 呆滞预警 (3)                                        │
│  ┌─────────────────────────────────────────────┐        │
│  │ ⚠️ ORD-20260620-003 焊接工序 停滞3天        │        │
│  │ ⚠️ ORD-20260618-007 质检工序 停滞5天        │        │
│  │ ⚠️ ORD-20260621-005 包装工序 停滞2天        │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│  🔥 加急订单                                            │
│  ┌─────────────────────────────────────────────┐        │
│  │ 🚨 ORD-20260622-010  李四工厂  明天交货     │        │
│  │ 🚨 ORD-20260620-008  王五科技  后天交货     │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│  📋 生产进度看板                                         │
│  ┌──────┬──────────┬──────────┬──────────┬──────────┐  │
│  │订单号│下料      │加工      │组装      │包装      │  │
│  ├──────┼──────────┼──────────┼──────────┼──────────┤  │
│  │001   │ ✅完成   │ ✅完成   │ 🔄进行中  │ ⏳待开工  │  │
│  │002   │ ✅完成   │ 🔄进行中  │ ⏳待开工  │ ⏳待开工  │  │
│  │003   │ 🔄进行中  │ ⏳待开工  │ ⏳待开工  │ ⏳待开工  │  │
│  │004   │ ⏳待开工  │ ⏳待开工  │ ⏳待开工  │ ⏳待开工  │  │
│  └──────┴──────────┴──────────┴──────────┴──────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 8. U盘自启动机制

### 8.1 start.bat

```batch
@echo off
chcp 65001 >nul
set SCRIPT_DIR=%~dp0
set DATA_DIR=%SCRIPT_DIR%data
set LOG_FILE=%DATA_DIR%service.log

echo ========================================
echo   Move Hermes - 智能订单管理系统
echo ========================================
echo.

REM 检查Python是否在PATH中
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 未检测到Python，正在安装...
    REM 内置Python便携版或下载链接
    echo [!] 请从 %SCRIPT_DIR%installer\ 目录运行安装程序
    pause
    exit /b 1
)

REM 检查数据目录
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

REM 检查API配置
if not exist "%DATA_DIR%api_config.json" (
    echo [*] 首次启动，正在打开配置页面...
    start "" "%SCRIPT_DIR%frontend\config.html"
) else (
    echo [*] 加载已有配置...
)

REM 启动服务
echo [*] 正在启动服务...
cd /d "%SCRIPT_DIR%backend"
python main.py >"%LOG_FILE%" 2>&1

REM 自动打开浏览器
timeout /t 3 /nobreak >nul
start "" "http://localhost:8080"

echo.
echo ========================================
echo   服务已启动，浏览器应已自动打开
echo   端口: 8080
echo   数据目录: %DATA_DIR%
echo ========================================
echo.
echo 提示: 关闭此窗口将停止服务
echo 安全弹出U盘前请先关闭服务
pause
```

### 8.2 优雅关闭

```batch
@echo off
echo 正在停止 Move Hermes 服务...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Move Hermes*" >nul 2>&1
echo 服务已停止，可以安全弹出U盘。
pause
```

### 8.3 服务生命周期

```
U盘插入 → Windows自动运行autorun.inf → 执行start.bat
    ↓
检测Python → 安装/跳过
    ↓
检测API配置 → 首次则打开配置页
    ↓
启动FastAPI服务 (端口8080)
    ↓
等待用户操作
    ↓
关闭窗口/手动停止 → 清理进程 → 安全弹出
```

---

## 9. 企微/飞书机器人集成

### 9.1 企微机器人

```python
# 基本流程：
# 1. 用户在企业微信群 @机器人 或发送图片
# 2. 企微推送消息到我们的回调URL
# 3. 后端接收 → 保存图片 → 调用AI识别
# 4. 识别结果写入数据库 → 更新订单/工序状态
# 5. 机器人回复确认消息

# 回调处理：
@app.post("/api/webhook/wecom")
async def wecom_callback(request: WecomRequest):
    if request.msgtype == "image":
        # 下载图片
        media_id = request.media_id
        image_url = await get_wecom_media(media_id)
        
        # 判断是订单照片还是工单照片
        # 通过企微用户的身份映射
        worker_name = get_worker_by_userid(request.userid)
        
        # AI识别
        result = await ai_parse_photo(image_url, context="production")
        
        # 更新工序状态
        await update_task_progress(result, worker_name)
        
        # 回复确认
        return WecomResponse(
            msgtype="text",
            text={"content": f"✅ 收到！{worker_name}的{result.task_name}工序已完成{result.quantity}件"}
        )
```

### 9.2 飞书机器人

```python
# 类似企微，使用飞书的Event订阅机制
# 订阅事件：im.message.receive_v1

@app.post("/api/webhook/feishu")
async def feishu_callback(event: FeishuEvent):
    message = event.event.message
    if message.message_type == "image":
        # 下载图片
        image_url = await get_feishu_image(message.content)
        
        # AI识别
        result = await ai_parse_photo(image_url, context="production")
        
        # 更新进度
        await update_task_progress(result)
        
        # 回复消息
        await reply_feishu_message(message.message_id, f"✅ 已记录：{result.summary}")
```

---

## 10. 后续扩展路线

### Phase 2 — 财务报表 Agent
- 订单数据 → 自动生成应收/应付账款
- 拍照发票 → AI识别 → 自动归类
- 月度利润表/资产负债表自动生成
- 报销审批流程

### Phase 3 — 仓库管理 Agent
- 原材料库存管理
- 成品库存管理
- 呆滞物料预警
- 库存盘点（拍照识别）

### Phase 4 — 智能增强
- 生产排程建议（基于订单优先级和产能）
- 成本估算（历史数据学习）
- 质量趋势分析

---

## 11. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| AI识别准确率不足 | 用户信任崩塌 | 始终保留人工复核入口；初期对低置信度结果强制人工确认 |
| U盘读写速度慢 | 用户体验差 | SQLite启用WAL模式；减少频繁写入；批量合并写入 |
| 断电/异常退出 | 数据损坏 | SQLite WAL模式自带原子性；每次写入后同步；定期备份 |
| 企微/飞书API变更 | 功能不可用 | 抽象适配器层；多平台兼容；降级为手动上传 |
| 用户不会配置API | 无法使用 | 提供预设模板；内置推荐模型；简化配置流程 |
| 数据安全问题 | 客户流失 | 数据仅存储在U盘本地；不上传任何业务数据；可选加密 |

---

## 12. 交付物清单

### MVP交付（订单跟踪）
- [x] 数据库Schema设计
- [x] API接口定义
- [x] AI提示词设计
- [ ] 后端代码实现
- [ ] 前端页面实现
- [ ] U盘自启动脚本
- [ ] 企微/飞书机器人集成
- [ ] 用户手册

### 后续交付
- [ ] 财务报表 Agent
- [ ] 仓库管理 Agent
- [ ] 移动端适配
- [ ] 数据导出/导入工具
- [ ] 多语言支持

---

**文档状态:** 初稿完成  
**下次迭代:** 进入工程评审 → 细化架构细节 → 开始编码实现
