# ingestion/daily_ingest.py
# Master ingestion script — pulls SST + Chl-a for the same dates
# Run this daily to keep the database current

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

# ── Fetch SST from NASA ────────────────────────────────────
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
        print(f"    SST error [{zone_id}]: {e}")
        return None

# ── Fetch Chl-a from Copernicus ───────────────────────────
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
        print(f"    Chl-a error [{zone_id}]: {e}")
        return None

# ── Store both signals together ────────────────────────────
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

# ── Main ───────────────────────────────────────────────────
def run(days_back=5):
    """
    Fetches SST + Chl-a together for the same dates.
    NASA MUR has 1-day lag, Copernicus has 8-day lag.
    So we fetch dates from (days_back+12) to 12 days ago
    to ensure both sources have data available.
    """
    print("=" * 58)
    print("AIRAVAT 3.0 — Daily Ingestion (SST + Chl-a)")
    print("=" * 58)

    print("\nConnecting to NASA Earthdata...")
    earthaccess.login(strategy="netrc")
    print("✅ NASA connected")
    print("✅ Copernicus connected (uses stored credentials)\n")

    conn = get_db()
    print("✅ Database connected\n")

    # Dates where BOTH sources have data (12+ day lag for Copernicus)
    dates = [
        (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(days_back + 12, 12, -1)
    ]

    total = 0
    for date_str in dates:
        print(f"📅 {date_str}")
        for zone_id, zone_config in ZONES.items():
            print(f"  {zone_config['name']}...", end=" ", flush=True)

            sst   = fetch_sst(zone_id, zone_config, date_str)
            chl_a = fetch_chl(zone_id, zone_config, date_str)

            if sst is not None or chl_a is not None:
                ts = datetime.strptime(date_str, "%Y-%m-%d")
                store(conn, zone_id, ts, sst, chl_a)
                print(f"SST={sst}°C  Chl-a={chl_a} mg/m³ ✅")
                total += 1
            else:
                print("no data ⚠️")

    conn.close()
    print(f"\n{'=' * 58}")
    print(f"Done — {total} observations stored")
    print(f"{'=' * 58}")

if __name__ == "__main__":
    run(days_back=5)