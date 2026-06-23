# Move Hermes — U盘智能体

面向20人以下小企业的AI驱动订单/财务/仓库管理系统。

## 快速开始

1. 将U盘插入电脑
2. 双击 `start.bat`
3. 首次启动会打开配置页面，输入AI API Key
4. 浏览器自动打开看板首页

## 项目结构

```
move-hermes/
├── backend/              # FastAPI 后端
│   ├── main.py           # 入口
│   ├── db_init.py        # 数据库初始化
│   ├── api_orders.py     # 订单API
│   └── services/         # 业务服务
│       └── ai_service.py # AI识别服务
├── frontend/             # 静态前端
│   ├── config.html       # 配置向导
│   └── dashboard.html    # 看板首页
├── data/                 # 运行时数据（U盘上的目录）
│   ├── move_hermes.db    # SQLite数据库
│   └── photos/           # 上传的照片
├── docs/                 # 设计文档
│   ├── design-doc-part*.md
│   ├── spec-order-tracking.md
│   ├── spec-financial-reports.md
│   └── spec-warehouse.md
├── start.bat             # 启动脚本
└── autorun.inf           # U盘自动运行
```

## 技术栈

- 后端: Python + FastAPI
- 数据库: SQLite (WAL模式)
- 前端: 原生HTML + Alpine.js + Tailwind CSS
- AI: 大模型API (GPT-4o/Claude/通义千问)
- 部署: 便携式U盘，双击启动

## 开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
cd backend
python main.py
# 访问 http://localhost:8080
```

## 模块路线图

1. **订单跟踪** (MVP) — 生产进度看板 + AI识别 + 预警
2. **财务报表** — 票据识别 + 应收应付 + 利润表
3. **仓库管理** — 库存管理 + 拍照盘点 + 预警
