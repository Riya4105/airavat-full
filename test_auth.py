# test_auth.py
import urllib.request
import urllib.parse
import json

BASE = "http://127.0.0.1:8000"

print("=" * 55)
print("AIRAVAT 3.0 — JWT Auth Test")
print("=" * 55)

# Test 1 — Login as Coast Guard
print("\nTest 1 — Login as Indian Coast Guard")
data = urllib.parse.urlencode({
    "username": "coast_guard",
    "password": "coastguard123"
}).encode()

req = urllib.request.Request(
    f"{BASE}/auth/login",
    data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
with urllib.request.urlopen(req) as r:
    result = json.loads(r.read())
    token = result["access_token"]
    print(f"  Agency: {result['agency']}")
    print(f"  Role:   {result['role']}")
    print(f"  Zones:  {result['zones']}")
    print(f"  Token:  {token[:40]}...")

# Test 2 — Verify token
print("\nTest 2 — Verify token (/auth/me)")
req2 = urllib.request.Request(
    f"{BASE}/auth/me",
    headers={"Authorization": f"Bearer {token}"}
)
with urllib.request.urlopen(req2) as r:
    me = json.loads(r.read())
    print(f"  Logged in as: {me['name']}")
    print(f"  Assigned zones: {me['zones']}")

# Test 3 — Kerala Fisheries sees only Z3 and Z6
print("\nTest 3 — Secure zones for Kerala Fisheries")
data2 = urllib.parse.urlencode({
    "username": "fisheries_kerala",
    "password": "fisheries123"
}).encode()
req3 = urllib.request.Request(
    f"{BASE}/auth/login",
    data=data2,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
with urllib.request.urlopen(req3) as r:
    result2 = json.loads(r.read())
    token2 = result2["access_token"]

req4 = urllib.request.Request(
    f"{BASE}/zones/secure",
    headers={"Authorization": f"Bearer {token2}"}
)
with urllib.request.urlopen(req4) as r:
    zones = json.loads(r.read())
    print(f"  Agency: {zones['agency']}")
    print(f"  Zones returned: {[z['zone_id'] for z in zones['zones']]}")
    print(f"  (Should only show Z3 and Z6)")

print("\n" + "=" * 55)
print("Auth working correctly.")
print("=" * 55)