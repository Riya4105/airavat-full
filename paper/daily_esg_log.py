# paper/daily_esg_log.py
# Logs daily ESG snapshots for paper analysis

import json
import os
import urllib.request
import time
from datetime import datetime, timezone

API = "https://airavat-full.onrender.com"
LOG_FILE = "paper/esg_history.jsonl"

os.makedirs("paper", exist_ok=True)

# Wake up Render first
print("Waking up API...")
for attempt in range(3):
    try:
        with urllib.request.urlopen(f"{API}/", timeout=30) as r:
            r.read()
        print("API awake.")
        break
    except Exception:
        print(f"  Attempt {attempt+1} failed, waiting 10s...")
        time.sleep(10)

# Now fetch zones
print("Fetching zone data...")
try:
    with urllib.request.urlopen(f"{API}/zones", timeout=60) as r:
        data = json.loads(r.read())

    entry = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": data["timestamp"],
        "zones": [
            {
                "zone_id": z["zone_id"],
                "zone_name": z["zone_name"],
                "alert_level": z["alert_level"],
                "best_match": z["best_match"],
                "chain_position": z["chain_position"],
                "chain_total": z["chain_total"],
                "priority": z["priority"],
                "latest_sst": z["latest_sst"],
                "latest_chl": z["latest_chl"],
                "vae_anomaly": z.get("vae_anomaly", 0)
            }
            for z in data["zones"]
        ]
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"Logged 7 zones for {entry['date']}")

except Exception as e:
    print(f"Failed to log snapshot: {e}")
    print("Run 'python paper\\daily_esg_log.py' manually to retry.")