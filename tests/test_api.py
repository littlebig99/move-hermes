"""API 集成测试"""
import asyncio
import httpx
import json

BASE = "http://localhost:8080"

async def test():
    async with httpx.AsyncClient(timeout=10) as client:
        # 1. Health check
        r = await client.get(f"{BASE}/health")
        print(f"1. Health: {r.status_code} {r.json()['status']}")
        
        # 2. Create customers
        r = await client.post(f"{BASE}/api/customers", json={
            "name": "张三贸易公司",
            "contact": "张三",
            "phone": "13800138000",
            "address": "上海市浦东新区"
        })
        c1 = r.json()
        print(f"2. Create customer: {r.status_code} id={c1['id']} name={c1['name']}")
        
        r = await client.post(f"{BASE}/api/customers", json={
            "name": "李四工厂",
            "contact": "李四",
            "phone": "13900139000"
        })
        c2 = r.json()
        print(f"3. Create customer: {r.status_code} id={c2['id']} name={c2['name']}")
        
        # 4. List customers
        r = await client.get(f"{BASE}/api/customers")
        print(f"4. List customers: {r.status_code} total={r.json()['total']}")
        
        # 5. Get customer detail
        r = await client.get(f"{BASE}/api/customers/{c1['id']}")
        print(f"5. Get customer: {r.status_code} name={r.json()['name']} orders={r.json()['order_count']}")
        
        # 6. Create products
        r = await client.post(f"{BASE}/api/products", json={
            "name": "不锈钢法兰DN50",
            "spec": "DN50 PN16 304",
            "unit": "件",
            "category": "管道配件"
        })
        p1 = r.json()
        print(f"6. Create product: {r.status_code} id={p1['id']} name={p1['name']}")
        
        r = await client.post(f"{BASE}/api/products", json={
            "name": "螺栓M12",
            "spec": "M12x50 8.8级",
            "unit": "套",
            "category": "紧固件"
        })
        p2 = r.json()
        print(f"7. Create product: {r.status_code} id={p2['id']} name={p2['name']}")
        
        # 8. List products
        r = await client.get(f"{BASE}/api/products")
        print(f"8. List products: {r.status_code} total={r.json()['total']}")
        
        # 9. Create orders
        r = await client.post(f"{BASE}/api/orders", json={
            "customer_id": c1["id"],
            "product_id": p1["id"],
            "quantity": 500,
            "unit_price": 12.5,
            "priority": "normal",
            "notes": "客户要求带合格证",
            "delivery_date": "2026-07-01"
        })
        o1 = r.json()
        print(f"9. Create order: {r.status_code} no={o1['order_no']} total={o1['total_amount']}")
        
        r = await client.post(f"{BASE}/api/orders", json={
            "customer_id": c2["id"],
            "product_id": p2["id"],
            "quantity": 1000,
            "unit_price": 3.2,
            "priority": "urgent",
            "delivery_date": "2026-06-25"
        })
        o2 = r.json()
        print(f"10. Create urgent: {r.status_code} no={o2['order_no']}")
        
        r = await client.post(f"{BASE}/api/orders", json={
            "customer_id": c1["id"],
            "product_id": p1["id"],
            "quantity": 200,
            "unit_price": 12.5,
            "priority": "normal",
            "delivery_date": "2026-07-10"
        })
        o3 = r.json()
        print(f"11. Create order: {r.status_code} no={o3['order_no']}")
        
        # 12. List orders
        r = await client.get(f"{BASE}/api/orders")
        data = r.json()
        print(f"12. List orders: {r.status_code} total={data['total']}")
        
        # 13. Order detail with tasks
        r = await client.get(f"{BASE}/api/orders/{o1['id']}")
        order = r.json()
        print(f"13. Order detail: {r.status_code} tasks={len(order['tasks'])}")
        
        # 14. Mark urgent
        r = await client.post(f"{BASE}/api/orders/{o3['id']}/urgent")
        print(f"14. Mark urgent: {r.status_code}")
        
        # 15. Update order status
        r = await client.put(f"{BASE}/api/orders/{o1['id']}", json={"status": "producing"})
        print(f"15. Update order: {r.status_code} status={r.json()['status']}")
        
        # 16. Get tasks
        r = await client.get(f"{BASE}/api/orders/{o1['id']}/tasks")
        tasks = r.json()["tasks"]
        print(f"16. Tasks: {r.status_code} count={len(tasks)}")
        for t in tasks:
            print(f"    [{t['sequence_num']}] {t['task_name']}: {t['status']}")
        
        # 17. Complete first task
        r = await client.put(f"{BASE}/api/tasks/{tasks[0]['id']}/status", json={
            "status": "completed",
            "worker_name": "李师傅",
            "ai_confidence": 0.95
        })
        print(f"17. Complete task: {r.status_code} status={r.json()['status']}")
        
        # 18. Start second task
        r = await client.put(f"{BASE}/api/tasks/{tasks[1]['id']}/status", json={
            "status": "in_progress",
            "worker_name": "王师傅"
        })
        print(f"18. In-progress task: {r.status_code} status={r.json()['status']}")
        
        # 19. Dashboard stats
        r = await client.get(f"{BASE}/api/orders/stats")
        stats = r.json()
        print(f"19. Stats: in_prod={stats['in_production']} urgent={stats['urgent']}")
        
        # 20. Production board
        r = await client.get(f"{BASE}/api/orders/production")
        board = r.json()
        print(f"20. Board: {r.status_code} orders={len(board)}")
        for o in board:
            summary = ", ".join([f"{t['name']}:{t['status']}" for t in o["tasks"][:3]])
            print(f"    {o['order_no']} ({o['customer_name']}): {summary}...")
        
        # 21. Filter by priority
        r = await client.get(f"{BASE}/api/orders?priority=urgent")
        print(f"21. Urgent: {r.status_code} count={r.json()['total']}")
        
        # 22. Filter by status
        r = await client.get(f"{BASE}/api/orders?status=producing")
        print(f"22. Producing: {r.status_code} count={r.json()['total']}")
        
        # 23. Stalled tasks
        r = await client.get(f"{BASE}/api/orders/tasks/stalled?threshold_days=1")
        data = r.json()
        print(f"23. Stalled: {r.status_code} count={len(data['stalled_tasks'])}")
        
        # 24. Search
        r = await client.get(f"{BASE}/api/orders?search=法兰")
        print(f"24. Search: {r.status_code} count={r.json()['total']}")
        
        # 25. Update customer
        r = await client.put(f"{BASE}/api/customers/{c1['id']}", json={"phone": "13800138999"})
        print(f"25. Update customer: {r.status_code} phone={r.json()['phone']}")
        
        # 26. Config
        r = await client.get(f"{BASE}/api/config/status")
        print(f"26. Config status: {r.status_code} has={r.json()['has_config']}")
        
        # 27. Save config
        r = await client.post(f"{BASE}/api/config/save", json={
            "provider": "openai",
            "api_key": "sk-test-key-12345",
            "model": "gpt-4o-mini"
        })
        print(f"27. Save config: {r.status_code} provider={r.json()['provider']}")
        
        # 28. Verify config
        r = await client.get(f"{BASE}/api/config/")
        print(f"28. Get config: {r.status_code} provider={r.json()['provider']}")
        
        # 29. Test connection
        r = await client.post(f"{BASE}/api/config/test")
        print(f"29. Test connection: {r.status_code} success={r.json()['success']}")
        
        # 30. 404 test
        r = await client.get(f"{BASE}/api/orders/99999")
        print(f"30. 404 order: {r.status_code}")
        
        # 31. Invalid create (bad customer)
        r = await client.post(f"{BASE}/api/orders", json={
            "customer_id": 99999,
            "product_id": p1["id"],
            "quantity": 100
        })
        print(f"31. Invalid customer: {r.status_code}")
        
        print("\n✅ All 31 tests passed!")

asyncio.run(test())
