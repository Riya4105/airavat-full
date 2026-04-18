# ingestion/nasa_sst.py
# Pulls real MUR SST data from NASA Earthdata for all 7 zones
# and stores it in TimescaleDB

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import earthaccess
import numpy as np
import psycopg2
import warnings
from datetime import datetime, timedelta
from config.zones import ZONES

warnings.filterwarnings("ignore")

# ── Database connection ────────────────────────────────────
CONN = {
    "host": "localhost",
    "port": 5432,
    "database": "airavat",
    "user": "airavat",
    "password": "airavat123"
}

def get_db():
    return psycopg2.connect(**CONN)

# ── NASA login ─────────────────────────────────────────────
def nasa_login():
    return earthaccess.login(strategy="netrc")

# ── Fetch SST for one zone ─────────────────────────────────
def fetch_sst_for_zone(zone_id, zone_config, date_str):
    """
    Fetches mean SST for a zone on a given date from NASA MUR dataset.
    Returns float (mean SST in Kelvin converted to Celsius) or None.
    """
    lon_min, lat_min, lon_max, lat_max = zone_config["bbox"]

    try:
        results = earthaccess.search_data(
            short_name="MUR-JPL-L4-GLOB-v4.1",
            temporal=(date_str, date_str),
            bounding_box=(lon_min, lat_min, lon_max, lat_max)
        )

        if not results:
            print(f"  [{zone_id}] No granules found for {date_str}")
            return None

        # Open the dataset directly without downloading
        ds = earthaccess.open(results)

        if not ds:
            return None

        import xarray as xr
        dataset = xr.open_dataset(ds[0], engine="h5netcdf")

        # Subset to our zone bounding box
        sst_subset = dataset["analysed_sst"].sel(
            lat=slice(lat_min, lat_max),
            lon=slice(lon_min, lon_max)
        )

        # Convert from Kelvin to Celsius and get mean
        sst_celsius = float(sst_subset.mean().values) - 273.15

        dataset.close()
        return round(sst_celsius, 3)

    except Exception as e:
        print(f"  [{zone_id}] Error fetching SST: {e}")
        return None

# ── Store observation in database ─────────────────────────
def store_observation(conn, zone_id, timestamp, sst, source="NASA_MUR"):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO zone_observations (time, zone_id, sst, source)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING;
    """, (timestamp, zone_id, sst, source))
    conn.commit()
    cursor.close()

# ── Main ingestion run ─────────────────────────────────────
def run_ingestion(days_back=3):
    """
    Fetches SST for all 7 zones for the last N days.
    Start with days_back=3 to test — increase to 90 for full baseline.
    """
    print("=" * 55)
    print("AIRAVAT 3.0 — NASA SST Ingestion")
    print("=" * 55)

    print("\nLogging into NASA Earthdata...")
    nasa_login()
    print("✅ NASA login successful\n")

    conn = get_db()
    print("✅ Database connected\n")

    # Generate date range
    dates = [
        (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(days_back, 0, -1)
    ]

    total_stored = 0

    for date_str in dates:
        print(f"📅 Processing {date_str}...")
        for zone_id, zone_config in ZONES.items():
            print(f"  Fetching {zone_config['name']}...", end=" ")
            sst = fetch_sst_for_zone(zone_id, zone_config, date_str)
            if sst is not None:
                timestamp = datetime.strptime(date_str, "%Y-%m-%d")
                store_observation(conn, zone_id, timestamp, sst)
                print(f"SST = {sst}°C ✅")
                total_stored += 1
            else:
                print("skipped ⚠️")

    conn.close()

    print(f"\n{'=' * 55}")
    print(f"Ingestion complete — {total_stored} observations stored")
    print(f"{'=' * 55}")

if __name__ == "__main__":
    run_ingestion(days_back=3)