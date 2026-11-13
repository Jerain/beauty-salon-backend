"""Debug failing endpoints."""
import httpx
import traceback

BASE = "http://localhost:8000"
client = httpx.Client(base_url=BASE, timeout=30.0)

r = client.post("/api/auth/login", json={"phone": "13800138000", "password": "123456"})
h = {"Authorization": f"Bearer {r.json()['access_token']}"}

endpoints = [
    ("GET", "/api/report/staff-data/list?month=2026-11"),
    ("GET", "/api/revisit-tasks/statistic"),
    ("GET", "/api/skin-tests/count"),
    ("GET", "/api/report/business/overview?start_date=2026-10-01&end_date=2026-11-03"),
    ("GET", "/api/report/revenue/detail?start_date=2026-10-01&end_date=2026-11-03"),
    ("GET", "/api/report/card-consumption?start_date=2026-10-01&end_date=2026-11-03"),
]

for method, url in endpoints:
    try:
        r = client.request(method, url, headers=h)
        status = r.status_code
        body = r.text[:300] if r.status_code != 200 else r.text[:150]
        print(f"\n{status} {method} {url}")
        if status != 200:
            print(f"  BODY: {body}")
    except Exception as e:
        print(f"\nERROR {method} {url}: {e}")

client.close()
