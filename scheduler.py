# scheduler.py
# Runs data ingestion every 6 hours automatically
# Keep this running alongside the API server

import schedule
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

def run_daily_ingest():
    log.info("Starting scheduled ingestion...")
    try:
        from ingestion.daily_ingest import run
        run(days_back=2)
        log.info("Ingestion complete")
    except Exception as e:
        log.error(f"Ingestion failed: {e}")

def run_baselines():
    log.info("Recomputing zone baselines...")
    try:
        from ingestion.compute_baselines import compute_baselines
        compute_baselines()
        log.info("Baselines updated")
    except Exception as e:
        log.error(f"Baseline update failed: {e}")

# Schedule ingestion every 6 hours
schedule.every(6).hours.do(run_daily_ingest)

# Recompute baselines once per day at midnight
schedule.every().day.at("00:00").do(run_baselines)

if __name__ == "__main__":
    log.info("=" * 50)
    log.info("AIRAVAT 3.0 — Scheduler started")
    log.info("Ingestion: every 6 hours")
    log.info("Baselines: daily at midnight")
    log.info("=" * 50)

    # Run once immediately on startup
    run_daily_ingest()
    run_baselines()

    # Then keep running on schedule
    while True:
        schedule.run_pending()
        time.sleep(60)