# ingestion/backfill.py
# Fetches 90 days of SST + Chl-a history for all 7 zones
# Run ONCE to build the zone personality baselines
# Takes approximately 2-3 hours — let it run in background

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import earthaccess
import copernicusmarine
import numpy as np
import psycopg2
import warnings
import xarray as xr
from datetime import datetime, timedelta
from config.zones import ZONES

warnings.filterwarnings("ignore")

CONN = {
    "host": "localhost",
    "port": 5432,
    "database": "airavat",
    "user": "airavat",
    "password": "airavat123"
}

def get_db():
    return psycopg2.connect(**CONN)

def fetch_sst(zone_id, zone_config, date_str):
    lon_min, lat_min, lon_max, lat_max = zone_config["bbox"]
    try:
        results = earthaccess.search_data(
            short_name="MUR-JPL-L4-GLOB-v4.1",
            temporal=(date_str, date_str),
            bounding_box=(lon_min, lat_min, lon_max, lat_max)
        )
        if not results:
            return None
        ds_files = earthaccess.open(results)
        if not ds_files:
            return None
        ds = xr.open_dataset(ds_files[0], engine="h5netcdf")
        sst = ds["analysed_sst"].sel(
            lat=slice(lat_min, lat_max),
            lon=slice(lon_min, lon_max)
        )
        val = float(sst.mean().values) - 273.15
        ds.close()
        return round(val, 3)
    except Exception as e:
        return None

def fetch_chl(zone_id, zone_config, date_str):
    lon_min, lat_min, lon_max, lat_max = zone_config["bbox"]
    try:
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
        chl = ds["CHL"].values
        chl_valid = chl[(chl > 0) & (chl < 100)]
        if len(chl_valid) == 0:
            return None
        val = round(float(np.nanmean(chl_valid)), 4)
        ds.close()
        return val
    except Exception as e:
        return None

def already_exists(conn, zone_id, date_str):
    """Skip dates we already have both signals for."""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM zone_observations
        WHERE zone_id = %s
          AND time::date = %s::date
          AND sst IS NOT NULL
          AND chl_a IS NOT NULL;
    """, (zone_id, date_str))
    count = cur.fetchone()[0]
    cur.close()
    return count > 0

def store(conn, zone_id, timestamp, sst, chl_a):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO zone_observations
            (time, zone_id, sst, chl_a, source)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING;
    """, (timestamp, zone_id, sst, chl_a, "NASA_MUR+COPERNICUS"))
    conn.commit()
    cur.close()

def run_backfill(days=90):
    print("=" * 58)
    print("AIRAVAT 3.0 — 90-Day Historical Backfill")
    print("=" * 58)
    print(f"\nFetching {days} days of history for 7 zones")
    print("Copernicus has 8-day lag — backfill starts 12 days ago")
    print("Estimated time: 2-3 hours")
    print("Safe to Ctrl+C and resume — skips existing rows\n")

    earthaccess.login(strategy="netrc")
    conn = get_db()
    print("✅ Connected to both sources and database\n")

    # Start from 12 days ago (Copernicus lag) going back 90 days
    dates = [
        (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(12, 12 + days)
    ]

    total = 0
    skipped = 0

    for d_idx, date_str in enumerate(dates):
        print(f"\n📅 [{d_idx+1}/{len(dates)}] {date_str}")

        for zone_id, zone_config in ZONES.items():

            # Skip if already in database
            if already_exists(conn, zone_id, date_str):
                print(f"  {zone_id} {zone_config['name'][:15]:<15} already exists — skipped")
                skipped += 1
                continue

            print(f"  {zone_id} {zone_config['name'][:15]:<15}", end=" ", flush=True)

            sst   = fetch_sst(zone_id, zone_config, date_str)
            chl_a = fetch_chl(zone_id, zone_config, date_str)

            if sst is not None or chl_a is not None:
                ts = datetime.strptime(date_str, "%Y-%m-%d")
                store(conn, zone_id, ts, sst, chl_a)
                print(f"SST={sst}°C  Chl-a={chl_a} ✅")
                total += 1
            else:
                print("no data ⚠️")

        # Progress summary every 10 days
        if (d_idx + 1) % 10 == 0:
            print(f"\n  --- Progress: {d_idx+1}/{len(dates)} days done | "
                  f"{total} stored | {skipped} skipped ---")

    conn.close()
    print(f"\n{'=' * 58}")
    print(f"Backfill complete — {total} new rows | {skipped} already existed")
    print(f"{'=' * 58}")

if __name__ == "__main__":
    run_backfill(days=90)