# ingestion/patch_missing_chl.py
# Fills in missing Chl-a for rows that have SST but no Chl-a

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import copernicusmarine
import numpy as np
import psycopg2
import warnings
from datetime import datetime
from config.zones import ZONES

warnings.filterwarnings("ignore")

CONN = {
    "host": "localhost", "port": 5432,
    "database": "airavat", "user": "airavat", "password": "airavat123"
}

def get_db():
    return psycopg2.connect(**CONN)

def fetch_chl(zone_id, zone_config, date_str):
    lon_min, lat_min, lon_max, lat_max = zone_config["bbox"]
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D",
            variables=["CHL"],
            minimum_longitude=lon_min, maximum_longitude=lon_max,
            minimum_latitude=lat_min,  maximum_latitude=lat_max,
            start_datetime=dt.strftime("%Y-%m-%dT00:00:00"),
            end_datetime=dt.strftime("%Y-%m-%dT23:59:59")
        )
        chl = ds["CHL"].values
        chl_valid = chl[(chl > 0) & (chl < 100)]
        ds.close()
        if len(chl_valid) == 0:
            return None
        return round(float(np.nanmean(chl_valid)), 4)
    except Exception as e:
        print(f"    [{zone_id}] {e}")
        return None

def run():
    print("Patching missing Chl-a values...")
    conn = get_db()
    cur = conn.cursor()

    # Find all rows missing Chl-a
    cur.execute("""
        SELECT DISTINCT zone_id, time::date
        FROM zone_observations
        WHERE chl_a IS NULL AND sst IS NOT NULL
        ORDER BY time::date, zone_id;
    """)
    missing = cur.fetchall()
    print(f"Found {len(missing)} rows missing Chl-a\n")

    patched = 0
    for zone_id, date in missing:
        date_str = date.strftime("%Y-%m-%d")
        print(f"  {zone_id} {date_str}...", end=" ", flush=True)
        chl = fetch_chl(zone_id, ZONES[zone_id], date_str)
        if chl:
            cur.execute("""
                UPDATE zone_observations
                SET chl_a = %s, source = 'NASA_MUR+COPERNICUS'
                WHERE zone_id = %s AND time::date = %s::date AND sst IS NOT NULL;
            """, (chl, zone_id, date_str))
            conn.commit()
            print(f"Chl-a={chl} ✅")
            patched += 1
        else:
            print("skipped ⚠️")

    cur.close()
    conn.close()
    print(f"\nPatched {patched} rows")

if __name__ == "__main__":
    run()