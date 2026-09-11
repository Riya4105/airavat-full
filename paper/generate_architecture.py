# paper/generate_architecture.py
# Generates Fig 2 — AIRAVAT System Architecture Block Diagram

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

os.makedirs('paper/figures', exist_ok=True)

fig, ax = plt.subplots(figsize=(16, 10))
fig.patch.set_facecolor('#0D1117')
ax.set_facecolor('#0D1117')
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis('off')

def box(x, y, w, h, color, label, sublabel=None, fontsize=10):
    rect = FancyBboxPatch((x, y), w, h,
                           boxstyle='round,pad=0.1',
                           facecolor=color, edgecolor='#30363D',
                           linewidth=1.5, zorder=3)
    ax.add_patch(rect)
    cy = y + h/2 + (0.15 if sublabel else 0)
    ax.text(x + w/2, cy, label,
            ha='center', va='center',
            color='white', fontsize=fontsize,
            fontweight='bold', zorder=4)
    if sublabel:
        ax.text(x + w/2, y + h/2 - 0.25, sublabel,
                ha='center', va='center',
                color='#8B949E', fontsize=7.5, zorder=4)

def arrow(x1, y1, x2, y2, color='#30363D'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color,
                                lw=1.5), zorder=2)

def dashed_box(x, y, w, h, color, label):
    rect = FancyBboxPatch((x, y), w, h,
                           boxstyle='round,pad=0.1',
                           facecolor='none', edgecolor=color,
                           linewidth=1.5, linestyle='--', zorder=2)
    ax.add_patch(rect)
    ax.text(x + w/2, y + h - 0.2, label,
            ha='center', va='top',
            color=color, fontsize=9,
            fontweight='bold', zorder=4)

# ── Title ──────────────────────────────────────────────
ax.text(8, 9.6, 'AIRAVAT 3.0 — System Architecture',
        ha='center', va='top', color='#9FE1CB',
        fontsize=14, fontweight='bold')

# ── Row 1: Data Sources ──────────────────────────────
ax.text(8, 9.1, 'DATA INGESTION LAYER',
        ha='center', va='top', color='#8B949E', fontsize=8,
        style='italic')

box(0.5, 8.0, 3.2, 0.85, '#0D2137',
    'NASA MUR SST', 'JPL L4 v4.1 · 1 km · Daily')
box(4.0, 8.0, 3.2, 0.85, '#0D2137',
    'Copernicus OLCI Chl-a', 'CMEMS L4 · 4 km · 8-day lag')
box(7.5, 8.0, 3.2, 0.85, '#0D2137',
    'Zone Averaging', '7 zones · Spatial mean · QC mask')
box(11.0, 8.0, 3.5, 0.85, '#052E26',
    'Supabase PostgreSQL', 'zone_observations · 188 obs/zone')

arrow(3.7, 8.42, 4.0, 8.42)
arrow(7.2, 8.42, 7.5, 8.42)
arrow(10.7, 8.42, 11.0, 8.42)

# ── Row 2: Baseline ──────────────────────────────────
ax.text(8, 7.7, 'ZONE PERSONALITY LAYER',
        ha='center', va='top', color='#8B949E', fontsize=8,
        style='italic')

box(5.5, 6.8, 5.0, 0.75, '#1C1A00',
    'Zone Baselines (90-day rolling)',
    'μ_SST, σ_SST, μ_Chl, σ_Chl per zone')

arrow(12.75, 8.0, 12.75, 7.55)
ax.annotate('', xy=(8.0, 7.55), xytext=(12.75, 7.55),
            arrowprops=dict(arrowstyle='->', color='#30363D', lw=1.5))

# ── Dashed box: Convergent Evidence Layer ────────────
dashed_box(0.3, 3.8, 15.4, 2.7, '#1D9E75',
           'CONVERGENT EVIDENCE LAYER')

# ── Row 3: Three parallel components ─────────────────
box(0.6, 4.2, 4.0, 2.0, '#052E26',
    'Multivariate DTW', 'SST/Chl-a · 6 templates\n60/40 weighting\nMagnitude normalisation\nChain position p ∈ {1…N}')
box(6.0, 4.2, 4.0, 2.0, '#0D1A2E',
    'VAE Zone Encoder', 'Input: 14-day window\nLatent dim: 8\nELBO training · 150 epochs\nReconstruction error → score')
box(11.4, 4.2, 4.0, 2.0, '#1A1528',
    'Slope Trajectory', 'OLS slope · last 3 obs\nSST trend direction\nNormalised 0–1\nFalse positive filter')

# Arrows from baseline to three components
for cx in [2.6, 8.0, 13.4]:
    arrow(8.0, 6.8, cx, 6.22)

# ── Row 4: Priority Score ────────────────────────────
box(5.0, 3.0, 6.0, 0.9, '#052E26',
    'Convergent Priority Score  P = 0.4·DTW + 0.35·VAE + 0.25·slope',
    'HIGH ≥ 0.55  |  WARN ≥ 0.35  |  NORMAL < 0.35')

# Arrows from three components to priority
for cx in [2.6, 8.0, 13.4]:
    arrow(cx, 4.2, 8.0, 3.9)

# ── Row 5: Alert + Dashboard ─────────────────────────
ax.text(8, 2.75, 'OPERATIONAL OUTPUT LAYER',
        ha='center', va='top', color='#8B949E', fontsize=8,
        style='italic')

box(0.5, 1.5, 3.5, 1.0, '#3D1F1F',
    'Auto Alert Loop', 'Every 30 min · Render 24/7\nTwilio SMS + WhatsApp\nDuplicate suppression')
box(4.5, 1.5, 3.5, 1.0, '#1A1528',
    'JWT Auth API', 'FastAPI · 4 agencies\nZone-level RBAC\nWebSocket live updates')
box(8.5, 1.5, 3.5, 1.0, '#052E26',
    'Live Dashboard', 'Leaflet.js · Chart.js\nPriority leaderboard\nChain progress display')
box(12.5, 1.5, 3.0, 1.0, '#0D1A2E',
    'NL Query Engine', 'Groq LLM · Rule-based\nMarine intelligence\nZone comparison')

arrow(8.0, 3.0, 8.0, 2.5)
ax.annotate('', xy=(2.25, 2.5), xytext=(8.0, 2.5),
            arrowprops=dict(arrowstyle='->', color='#30363D', lw=1.5))
ax.annotate('', xy=(6.25, 2.5), xytext=(8.0, 2.5),
            arrowprops=dict(arrowstyle='->', color='#30363D', lw=1.5))
ax.annotate('', xy=(10.25, 2.5), xytext=(8.0, 2.5),
            arrowprops=dict(arrowstyle='->', color='#30363D', lw=1.5))
ax.annotate('', xy=(14.0, 2.5), xytext=(8.0, 2.5),
            arrowprops=dict(arrowstyle='->', color='#30363D', lw=1.5))

for cx in [2.25, 6.25, 10.25, 14.0]:
    arrow(cx, 2.5, cx, 2.5)

# ── Legend ────────────────────────────────────────────
legend_items = [
    mpatches.Patch(facecolor='#0D2137', edgecolor='#30363D', label='Data sources'),
    mpatches.Patch(facecolor='#052E26', edgecolor='#30363D', label='ESG engine'),
    mpatches.Patch(facecolor='#0D1A2E', edgecolor='#30363D', label='ML components'),
    mpatches.Patch(facecolor='#3D1F1F', edgecolor='#30363D', label='Alert dispatch'),
    mpatches.Patch(facecolor='none',    edgecolor='#1D9E75',
                   linestyle='--', label='Convergent evidence layer'),
]
ax.legend(handles=legend_items, loc='lower left',
           fontsize=8, facecolor='#161B22',
           edgecolor='#30363D', labelcolor='#E6EDF3',
           ncol=5, bbox_to_anchor=(0.0, 0.0))

plt.tight_layout()
plt.savefig('paper/figures/fig2_architecture.pdf', dpi=300,
            bbox_inches='tight', facecolor='#0D1117')
plt.savefig('paper/figures/fig2_architecture.png', dpi=300,
            bbox_inches='tight', facecolor='#0D1117')
print("Fig 2 architecture diagram saved to paper/figures/")
plt.close()