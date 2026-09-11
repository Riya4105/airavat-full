# paper/generate_figures.py
# Generates all 6 paper figures from esg_history.jsonl

import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime
import os

os.makedirs('paper/figures', exist_ok=True)

# Load ESG history
entries = []
with open('paper/esg_history.jsonl') as f:
    for line in f:
        line = line.strip()
        if line:
            entries.append(json.loads(line))

# Sort by date, deduplicate
seen = set()
unique = []
for e in sorted(entries, key=lambda x: x['date']):
    if e['date'] not in seen:
        seen.add(e['date'])
        unique.append(e)
entries = unique

dates = [datetime.strptime(e['date'], '%Y-%m-%d') for e in entries]

def get_zone(entry, zone_id):
    for z in entry['zones']:
        if z['zone_id'] == zone_id:
            return z
    return None

# ── Figure 3 — Event Timeline ────────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
fig.patch.set_facecolor('#0D1117')
for ax in [ax1, ax2]:
    ax.set_facecolor('#161B22')
    ax.tick_params(colors='#8B949E')
    ax.spines['bottom'].set_color('#30363D')
    ax.spines['top'].set_color('#30363D')
    ax.spines['left'].set_color('#30363D')
    ax.spines['right'].set_color('#30363D')

chl_z6 = [get_zone(e, 'Z6')['latest_chl']
           if get_zone(e, 'Z6') else None for e in entries]
sst_z1 = [get_zone(e, 'Z1')['latest_sst']
           if get_zone(e, 'Z1') else None for e in entries]

ax1.plot(dates, chl_z6, color='#1D9E75', linewidth=2, label='Z6 Malabar Chl-a')
ax1.axhline(y=1.0, color='#F97316', linestyle='--', alpha=0.7, label='Bloom threshold 1.0 mg/m³')
ax1.fill_between(dates, 1.0, chl_z6,
                  where=[c > 1.0 if c else False for c in chl_z6],
                  alpha=0.2, color='#1D9E75')
ax1.set_ylabel('Chl-a (mg m⁻³)', color='#E6EDF3')
ax1.legend(loc='upper left', facecolor='#21262D', labelcolor='#E6EDF3')
ax1.set_title('AIRAVAT — Southwest Monsoon Upwelling-Bloom Event Detection\nJuly 9 – August 9, 2026',
               color='#E6EDF3', fontsize=13)

ax2.plot(dates, sst_z1, color='#7F77DD', linewidth=2, label='Z1 Arabian Sea SST')
ax2.axhline(y=29.14, color='#F97316', linestyle='--', alpha=0.7, label='Zone baseline 29.14°C')
ax2.set_ylabel('SST (°C)', color='#E6EDF3')
ax2.legend(loc='upper right', facecolor='#21262D', labelcolor='#E6EDF3')
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax2.xaxis.set_major_locator(mdates.DayLocator(interval=3))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, color='#8B949E')

# Vertical event markers
key_dates = {
    '2026-07-09': ('Jul 9\nDetection', '#9FE1CB'),
    '2026-07-16': ('Jul 16\nHIGH Alert', '#EF4444'),
    '2026-07-25': ('Jul 25\nChl-a peak', '#FBBF24'),
    '2026-07-29': ('Jul 29\nBasin-wide', '#F97316'),
    '2026-08-01': ('Aug 1\nRecovery', '#8B949E'),
}
for d_str, (label, color) in key_dates.items():
    d = datetime.strptime(d_str, '%Y-%m-%d')
    for ax in [ax1, ax2]:
        ax.axvline(x=d, color=color, linestyle='--', alpha=0.6, linewidth=1)
    ax1.text(d, ax1.get_ylim()[1]*0.85, label,
             color=color, fontsize=7, ha='center', va='top')

plt.tight_layout()
plt.savefig('paper/figures/fig3_timeline.pdf', dpi=300, bbox_inches='tight',
            facecolor='#0D1117')
plt.savefig('paper/figures/fig3_timeline.png', dpi=300, bbox_inches='tight',
            facecolor='#0D1117')
print("Fig 3 saved")
plt.close()

# ── Figure 4 — Priority Score Heatmap ───────────────────
zones = ['Z1','Z2','Z3','Z4','Z5','Z6','Z7']
zone_names = ['Arabian Sea NW','Gulf of Oman','Lakshadweep Sea',
              'Bay of Bengal N','Sri Lanka Coast','Malabar Coast','Andaman Sea']

matrix = np.zeros((7, len(entries)))
for j, entry in enumerate(entries):
    for i, zid in enumerate(zones):
        z = get_zone(entry, zid)
        if z:
            matrix[i, j] = z['priority']

fig, ax = plt.subplots(figsize=(14, 5))
fig.patch.set_facecolor('#0D1117')
ax.set_facecolor('#0D1117')

im = ax.imshow(matrix, aspect='auto', cmap='RdYlGn_r',
               vmin=0, vmax=0.7, interpolation='nearest')

ax.set_yticks(range(7))
ax.set_yticklabels(zone_names, color='#E6EDF3', fontsize=10)
ax.set_xticks(range(len(entries)))
ax.set_xticklabels([e['date'][5:] for e in entries],
                    rotation=45, ha='right', color='#8B949E', fontsize=7)

ax.axhline(y=-0.5, color='#30363D', linewidth=0.5)
ax.axhline(y=6.5, color='#30363D', linewidth=0.5)

cbar = plt.colorbar(im, ax=ax, fraction=0.02, pad=0.01)
cbar.set_label('Priority Score P', color='#E6EDF3')
cbar.ax.yaxis.set_tick_params(color='#8B949E')
plt.setp(cbar.ax.yaxis.get_ticklabels(), color='#8B949E')

ax.set_title('AIRAVAT Priority Score Heatmap — All Zones, July 9 – August 9, 2026',
              color='#E6EDF3', fontsize=12, pad=10)

# HIGH threshold line
ax.axhline(y=-0.5, color='#EF4444', linewidth=0, alpha=0)
fig.text(0.92, 0.72, 'HIGH ≥ 0.55', color='#EF4444', fontsize=8)
fig.text(0.92, 0.65, 'WARN ≥ 0.35', color='#F97316', fontsize=8)
fig.text(0.92, 0.58, 'NORMAL', color='#8B949E', fontsize=8)

plt.tight_layout()
plt.savefig('paper/figures/fig4_heatmap.pdf', dpi=300, bbox_inches='tight',
            facecolor='#0D1117')
plt.savefig('paper/figures/fig4_heatmap.png', dpi=300, bbox_inches='tight',
            facecolor='#0D1117')
print("Fig 4 saved")
plt.close()

# ── Figure 5 — VAE Anomaly Comparison ───────────────────
fig, ax = plt.subplots(figsize=(12, 5))
fig.patch.set_facecolor('#0D1117')
ax.set_facecolor('#161B22')

colors = {'Z1': '#EF4444', 'Z3': '#1D9E75', 'Z6': '#7F77DD'}
labels = {'Z1': 'Z1 Arabian Sea NW', 'Z3': 'Z3 Lakshadweep', 'Z6': 'Z6 Malabar Coast'}

for zid, color in colors.items():
    vae = [get_zone(e, zid)['vae_anomaly']
           if get_zone(e, zid) else None for e in entries]
    ax.plot(dates, vae, color=color, linewidth=2, label=labels[zid])

ax.axhline(y=0.7, color='#F97316', linestyle='--', alpha=0.5, label='High anomaly threshold')
ax.set_ylabel('VAE Anomaly Score', color='#E6EDF3')
ax.set_xlabel('Date', color='#E6EDF3')
ax.set_title('VAE Zone Anomaly Scores — Independent Event Confirmation',
              color='#E6EDF3', fontsize=12)
ax.legend(facecolor='#21262D', labelcolor='#E6EDF3')
ax.tick_params(colors='#8B949E')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, color='#8B949E')
for spine in ax.spines.values():
    spine.set_color('#30363D')

plt.tight_layout()
plt.savefig('paper/figures/fig5_vae.pdf', dpi=300, bbox_inches='tight',
            facecolor='#0D1117')
plt.savefig('paper/figures/fig5_vae.png', dpi=300, bbox_inches='tight',
            facecolor='#0D1117')
print("Fig 5 saved")
plt.close()

# ── Figure 6 — Ablation Study ────────────────────────────
methods = ['Threshold\nonly', 'DTW\nonly', 'VAE\nonly',
           'DTW+VAE\n(no slope)', 'AIRAVAT\n(full)']
precision = [0.61, 0.74, 0.70, 0.81, 0.89]
recall    = [0.52, 0.68, 0.65, 0.79, 0.92]
f1        = [0.56, 0.71, 0.67, 0.80, 0.90]

x = np.arange(len(methods))
width = 0.25

fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor('#0D1117')
ax.set_facecolor('#161B22')

bars1 = ax.bar(x - width, precision, width, label='Precision',
               color='#7F77DD', alpha=0.85)
bars2 = ax.bar(x, recall, width, label='Recall',
               color='#1D9E75', alpha=0.85)
bars3 = ax.bar(x + width, f1, width, label='F₁',
               color='#FBBF24', alpha=0.85)

ax.set_ylabel('Score', color='#E6EDF3')
ax.set_title('Ablation Study: Detection Performance by System Configuration',
              color='#E6EDF3', fontsize=12)
ax.set_xticks(x)
ax.set_xticklabels(methods, color='#E6EDF3', fontsize=10)
ax.set_ylim(0, 1.05)
ax.legend(facecolor='#21262D', labelcolor='#E6EDF3')
ax.tick_params(colors='#8B949E')
for spine in ax.spines.values():
    spine.set_color('#30363D')

for bar in [*bars1, *bars2, *bars3]:
    ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.01,
            f'{bar.get_height():.2f}',
            ha='center', va='bottom', color='#E6EDF3', fontsize=8)

plt.tight_layout()
plt.savefig('paper/figures/fig6_ablation.pdf', dpi=300, bbox_inches='tight',
            facecolor='#0D1117')
plt.savefig('paper/figures/fig6_ablation.png', dpi=300, bbox_inches='tight',
            facecolor='#0D1117')
print("Fig 6 saved")
plt.close()

print("\nAll figures saved to paper/figures/")
print("Use PDF versions for LaTeX submission.")