## 5. API接口设计

### 5.1 核心API

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

### 5.2 AI识别返回格式

```json
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
