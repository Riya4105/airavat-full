# test_alerts.py
import urllib.request
import urllib.parse
import json

BASE = "http://127.0.0.1:8000"

print("=" * 55)
print("AIRAVAT 3.0 — Alert Dispatch Test")
print("=" * 55)

# Step 1 — Login
data = urllib.parse.urlencode({
    "username": "thalassa_admin",
    "password": "thalassa2026"
}).encode()

req = urllib.request.Request(
    f"{BASE}/auth/login",
    data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
with urllib.request.urlopen(req) as r:
    result = json.loads(r.read())
    token = result["access_token"]
    print(f"Logged in as: {result['agency']}")

# Step 2 — Dispatch SMS alert for Z1
print("\nDispatching SMS alert for Z1...")
req2 = urllib.request.Request(
    f"{BASE}/alert/dispatch?zone_id=Z1&channel=sms",
    method="POST",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Length": "0"
    }
)
with urllib.request.urlopen(req2) as r:
    result2 = json.loads(r.read())
    print(f"Zone: {result2['zone_name']}")
    print(f"Alert level: {result2['alert_level']}")
    print(f"Results: {result2['results']}")
    print(f"\nMessage sent:")
    print(result2['message'])

print("\n" + "=" * 55)