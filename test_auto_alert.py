# test_auto_alert.py
from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.insert(0, '.')

from esg_engine.dtw_matcher import run_all_zones
from api.alerts import dispatch_alert
from api.auth import AGENCIES

print("Scanning all zones for HIGH alerts...")
results = run_all_zones()
high = [z for z in results if z["alert_level"] == "HIGH"]

print(f"HIGH zones found: {len(high)}")

for z in high:
    print(f"\nZone: {z['zone_name']} — priority {z['priority']}")
    for agency_id, agency in AGENCIES.items():
        if z["zone_id"] in agency["zones"]:
            print(f"  Dispatching to {agency['name']}...")
            r = dispatch_alert(z, agency_id, "sms")
            for result in r:
                print(f"  Result: {result}")

if not high:
    print("No HIGH zones right now — all WARN or NORMAL")
    print("Showing top zone:")
    top = results[0]
    print(f"  {top['zone_name']} — {top['alert_level']} — priority {top['priority']}")