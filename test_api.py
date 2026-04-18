# test_api.py
import urllib.request
import json

BASE = "http://127.0.0.1:8000"

# Test 1 — Health check
print("=" * 55)
print("Test 1 — Health Check")
with urllib.request.urlopen(f"{BASE}/") as r:
    data = json.loads(r.read())
    print(f"  Status:  {data['status']}")
    print(f"  System:  {data['system']}")
    print(f"  Source:  {data['data_source']}")

# Test 2 — All zones
print("\nTest 2 — All Zones Ranked")
with urllib.request.urlopen(f"{BASE}/zones") as r:
    data = json.loads(r.read())
    for z in data["zones"]:
        print(f"  {z['zone_name']:<22} {z['alert_level']:<8} priority={z['priority']}")

# Test 3 — Single zone
print("\nTest 3 — Zone Z1 Detail")
with urllib.request.urlopen(f"{BASE}/zones/Z1") as r:
    z = json.loads(r.read())
    print(f"  Zone:        {z['zone_name']}")
    print(f"  Alert:       {z['alert_level']}")
    print(f"  Event:       {z['best_match']}")
    print(f"  Chain:       Step {z['chain_position']} of {z['chain_total']}")
    print(f"  Priority:    {z['priority']}")
    print(f"  SST:         {z['latest_sst']}°C")
    print(f"  Chl-a:       {z['latest_chl']} mg/m³")

# Test 4 — Baselines
print("\nTest 4 — Zone Baselines")
with urllib.request.urlopen(f"{BASE}/baseline") as r:
    data = json.loads(r.read())
    for b in data["baselines"]:
        print(f"  {b['zone_id']} {b['zone_name']:<22} "
              f"SST={b['mean_sst']}°C  Chl-a={b['mean_chl_a']} mg/m³")

print("\n" + "=" * 55)
print("All endpoints responding correctly.")
print("=" * 55)