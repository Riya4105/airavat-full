# ingestion/compute_baselines.py
# Computes zone personality baselines from 90-day real satellite history
# Run after backfill — updates zone_baselines table

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import numpy as np
from datetime import datetime, timedelta, timezone
from config.zones import ZONES

CONN = {
    "host": "localhost",
    "port": 5432,
    "database": "airavat",
    "user": "airavat",
    "password": "airavat123"
}

def compute_baselines():
    print("=" * 58)
    print("AIRAVAT 3.0 — Zone Baseline Calculator")
    print("=" * 58)

    conn = psycopg2.connect(**CONN)
    cur = conn.cursor()

    # Use last 90 days of real data
    from datetime import timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=92)).strftime("%Y-%m-%d")

    print(f"\nComputing baselines from data since {cutoff}\n")

    for zone_id, zone_config in ZONES.items():

        # Fetch all SST and Chl-a for this zone
        cur.execute("""
            SELECT sst, chl_a
            FROM zone_observations
            WHERE zone_id = %s
              AND time >= %s
              AND sst IS NOT NULL
              AND chl_a IS NOT NULL
            ORDER BY time;
        """, (zone_id, cutoff))

        rows = cur.fetchall()

        if len(rows) < 10:
            print(f"  {zone_id} {zone_config['name']:<20} insufficient data ({len(rows)} rows) ⚠️")
            continue

        sst_vals  = np.array([r[0] for r in rows])
        chl_vals  = np.array([r[1] for r in rows])

        mean_sst   = round(float(np.mean(sst_vals)),  4)
        std_sst    = round(float(np.std(sst_vals)),   4)
        mean_chl   = round(float(np.mean(chl_vals)),  4)
        std_chl    = round(float(np.std(chl_vals)),   4)

        # Upsert into zone_baselines
        cur.execute("""
            INSERT INTO zone_baselines
                (zone_id, mean_sst, std_sst, mean_chl_a, std_chl_a, last_updated)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (zone_id) DO UPDATE SET
                mean_sst     = EXCLUDED.mean_sst,
                std_sst      = EXCLUDED.std_sst,
                mean_chl_a   = EXCLUDED.mean_chl_a,
                std_chl_a    = EXCLUDED.std_chl_a,
                last_updated = NOW();
        """, (zone_id, mean_sst, std_sst, mean_chl, std_chl))

        conn.commit()

        print(f"  {zone_id} {zone_config['name']:<20} "
              f"SST={mean_sst}±{std_sst}°C  "
              f"Chl-a={mean_chl}±{std_chl} mg/m³  "
              f"({len(rows)} obs) ✅")

    cur.close()
    conn.close()

    print(f"\n{'=' * 58}")
    print("Zone baselines saved to database.")
    print("Zone personality layer is now running on real data.")
    print(f"{'=' * 58}")

if __name__ == "__main__":
    compute_baselines()