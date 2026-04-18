# test_esg.py
# Tests the ESG engine against real database observations

from esg_engine.dtw_matcher import run_all_zones

print("=" * 65)
print("AIRAVAT 3.0 — ESG Engine Test (Real Data)")
print("=" * 65)

results = run_all_zones()

print(f"\n{'RANK':<5} {'ZONE':<22} {'EVENT':<18} {'PRIORITY':<10} {'ALERT':<8} {'CHAIN'}")
print("-" * 80)

for i, r in enumerate(results):
    print(
        f"  {i+1:<4} "
        f"{r['zone_name']:<22} "
        f"{r['best_match']:<18} "
        f"{r['priority']:<10} "
        f"{r['alert_level']:<8} "
        f"Step {r['chain_position']}/{r['chain_total']}"
    )

print("\n" + "=" * 65)
print("Top zone details:")
top = results[0]
print(f"  Zone:        {top['zone_name']}")
print(f"  Event type:  {top['best_match']}")
print(f"  Priority:    {top['priority']}")
print(f"  Alert level: {top['alert_level']}")
print(f"  Chain:       Step {top['chain_position']} of {top['chain_total']}")
print(f"  Description: {top['chain_description']}")
print(f"  Latest SST:  {top['latest_sst']}°C")
print(f"  Latest Chl-a:{top['latest_chl']} mg/m³")
print("=" * 65)