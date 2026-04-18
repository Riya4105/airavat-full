# test_connections.py
# Run anytime to verify both data source connections are working

import copernicusmarine
import earthaccess
import warnings
warnings.filterwarnings("ignore")  # suppress FutureWarning noise

print("=" * 50)
print("AIRAVAT 3.0 — Connection Test")
print("=" * 50)

# ── Copernicus Marine ──────────────────────────────
print("\n[1] Copernicus Marine Service...")
try:
    datasets = copernicusmarine.describe(
        contains=["OCEANCOLOUR_IND"],
        disable_progress_bar=True
    )
    print("    ✅ Connected successfully")
except Exception as e:
    print(f"    ❌ Error: {e}")

# ── NASA Earthdata ─────────────────────────────────
print("\n[2] NASA Earthdata (MUR SST)...")
try:
    auth = earthaccess.login(strategy="netrc")
    results = earthaccess.search_data(
        short_name="MUR-JPL-L4-GLOB-v4.1",
        temporal=("2024-01-01", "2024-01-03"),
        bounding_box=(55, 15, 65, 25)
    )
    print(f"    ✅ Connected — {len(results)} granules found for Z1 (Arabian Sea NW)")
except Exception as e:
    print(f"    ❌ Error: {e}")

print("\n" + "=" * 50)
print("Step 1 complete. Ready for TimescaleDB setup.")
print("=" * 50)