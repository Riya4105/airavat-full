# ingestion/copernicus_chl.py
# Pulls real Chlorophyll-a data from Copernicus Marine Service
# for all 7 zones and stores in TimescaleDB

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import copernicusmarine
import numpy as np
import psycopg2
import warnings
from datetime import datetime, timedelta
from config.zones import ZONES

warnings.filterwarnings("ignore")

import os
from urllib.parse import urlparse

def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        parsed = urlparse(db_url)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            sslmode="require"
        )
    else:
        return psycopg2.connect(
            host="localhost", port=5432,
            database="airavat", user="airavat",
            password="airavat123"
        )

def fetch_chl_for_zone(zone_id, zone_config, date_str):
    """
    Fetches mean Chl-a for a zone on a given date from Copernicus.
    Returns float (mg/m³) or None.
    """
    lon_min, lat_min, lon_max, lat_max = zone_config["bbox"]

    try:
        # Parse date
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        start = dt.strftime("%Y-%m-%dT00:00:00")
        end   = dt.strftime("%Y-%m-%dT23:59:59")

        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D",
            variables=["CHL"],
            minimum_longitude=lon_min,
            maximum_longitude=lon_max,
            minimum_latitude=lat_min,
            maximum_latitude=lat_max,
            start_datetime=start,
            end_datetime=end
        )

        chl_values = ds["CHL"].values
        # Filter out fill values (very large numbers or negatives)
        chl_valid = chl_values[
            (chl_values > 0) & (chl_values < 100)
        ]

        if len(chl_valid) == 0:
            return None

        chl_mean = round(float(np.nanmean(chl_valid)), 4)
        ds.close()
        return chl_mean

    except Exception as e:
        print(f"  [{zone_id}] Chl-a error: {e}")
        return None

def update_chl_observation(conn, zone_id, timestamp, chl_a):
    """Updates existing row with chl_a value, or inserts if missing."""
    cursor = conn.cursor()
    # Try to update existing row first
    cursor.execute("""
        UPDATE zone_observations
        SET chl_a = %s
        WHERE zone_id = %s
          AND time::date = %s::date
          AND source = 'NASA_MUR';
    """, (chl_a, zone_id, timestamp))

    # If no row existed, insert a new one
    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO zone_observations
                (time, zone_id, chl_a, source)
            VALUES (%s, %s, %s, %s);
        """, (timestamp, zone_id, chl_a, "COPERNICUS_CHL"))

    conn.commit()
    cursor.close()

def run_chl_ingestion(days_back=3):
    print("=" * 55)
    print("AIRAVAT 3.0 — Copernicus Chl-a Ingestion")
    print("=" * 55)

    conn = get_db()
    print("✅ Database connected\n")

    # Copernicus MY dataset has ~8 day lag — start from 12 days ago to be safe
    dates = [
        (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(days_back + 12, 12, -1)
    ]

    total_updated = 0

    for date_str in dates:
        print(f"📅 Processing {date_str}...")
        for zone_id, zone_config in ZONES.items():
            print(f"  Fetching Chl-a {zone_config['name']}...", end=" ")
            chl = fetch_chl_for_zone(zone_id, zone_config, date_str)
            if chl is not None:
                timestamp = datetime.strptime(date_str, "%Y-%m-%d")
                update_chl_observation(conn, zone_id, timestamp, chl)
                print(f"Chl-a = {chl} mg/m³ ✅")
                total_updated += 1
            else:
                print("skipped ⚠️")

    conn.close()
    print(f"\n{'=' * 55}")
    print(f"Chl-a ingestion complete — {total_updated} observations updated")
    print(f"{'=' * 55}")

if __name__ == "__main__":
    run_chl_ingestion(days_back=3)