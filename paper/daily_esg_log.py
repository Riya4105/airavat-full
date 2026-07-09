# paper/daily_esg_log.py
# Logs daily ESG snapshots for paper analysis
# Run after daily_update.ps1 every day

import json
import os
import urllib.request
from datetime import datetime, timezone

API = "https://airavat-full.onrender.com"
LOG_FILE = "paper/esg_history.jsonl"

os.makedirs("paper", exist_ok=True)

with urllib.request.urlopen(f"{API}/zones") as r:
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

print(f"Logged {len(entry['zones'])} zones for {entry['date']}")