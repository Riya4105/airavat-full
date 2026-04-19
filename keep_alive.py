# keep_alive.py
# Pings the Render API every 14 minutes to prevent cold starts
# Run this on your machine while developing or deploy as a cron job

import urllib.request
import time
from datetime import datetime

URL = "https://airavat-full.onrender.com/"
INTERVAL = 14 * 60  # 14 minutes

print(f"Keep-alive started — pinging {URL} every 14 minutes")

while True:
    try:
        with urllib.request.urlopen(URL, timeout=30) as r:
            print(f"{datetime.now().strftime('%H:%M:%S')} — API awake ({r.status})")
    except Exception as e:
        print(f"{datetime.now().strftime('%H:%M:%S')} — Ping failed: {e}")
    time.sleep(INTERVAL)