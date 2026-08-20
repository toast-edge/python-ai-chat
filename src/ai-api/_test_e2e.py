import json
from fastapi.testclient import TestClient
import api_server

c = TestClient(api_server.app)

question = "支付宝账单总共有多少笔交易，总金额是多少？"
print("问题:", question)
print("查询中...（AI 生成 SQL + 执行 + 总结）\n")

r = c.post("/query", json={"question": question})
print("HTTP", r.status_code)
data = r.json()
print(json.dumps(data, ensure_ascii=False, indent=2))