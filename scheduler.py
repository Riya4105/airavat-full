# scheduler.py
# Runs data ingestion every 6 hours and auto-alerts on HIGH zones

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

# Track which zones have already been alerted to avoid repeat SMS
alerted_zones = set()

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

def check_and_alert():
    """
    Scans all zones for HIGH alerts and dispatches SMS.
    Only alerts once per zone until it drops back to WARN/NORMAL.
    """
    log.info("Scanning zones for HIGH alerts...")
    try:
        from esg_engine.dtw_matcher import run_all_zones
        from api.alerts import dispatch_alert

        results = run_all_zones()
        high_zones = [z for z in results if z["alert_level"] == "HIGH"]
        normal_zones = {z["zone_id"] for z in results if z["alert_level"] != "HIGH"}

        # Clear alert tracking for zones that have recovered
        for zone_id in normal_zones:
            alerted_zones.discard(zone_id)

        # Alert for new HIGH zones
        for zone in high_zones:
            zone_id = zone["zone_id"]
            if zone_id not in alerted_zones:
                log.info(f"HIGH alert — {zone['zone_name']} priority={zone['priority']}")

                # Dispatch to all agencies that have this zone assigned
                from api.auth import AGENCIES
                for agency_id, agency in AGENCIES.items():
                    if zone_id in agency["zones"]:
                        dispatch_results = dispatch_alert(zone, agency_id, "sms")
                        for r in dispatch_results:
                            if r.get("status") == "sent":
                                log.info(f"SMS sent to {r['to']} for {zone['zone_name']}")
                            elif r.get("status") == "failed":
                                log.error(f"SMS failed to {r['to']}: {r.get('error')}")

                alerted_zones.add(zone_id)
            else:
                log.info(f"Zone {zone_id} still HIGH — already alerted, skipping")

        if not high_zones:
            log.info("All zones WARN/NORMAL — no alerts needed")

    except Exception as e:
        log.error(f"Alert check failed: {e}")

# ── Schedule ───────────────────────────────────────────────
schedule.every(6).hours.do(run_daily_ingest)
schedule.every().day.at("00:00").do(run_baselines)
schedule.every(30).minutes.do(check_and_alert)

if __name__ == "__main__":
    log.info("=" * 55)
    log.info("AIRAVAT 3.0 — Scheduler + Auto-Alert started")
    log.info("Ingestion:    every 6 hours")
    log.info("Baselines:    daily at midnight")
    log.info("Alert check:  every 30 minutes")
    log.info("=" * 55)

    # Run immediately on startup
    run_daily_ingest()
    run_baselines()
    check_and_alert()

    while True:
        schedule.run_pending()
        time.sleep(60)