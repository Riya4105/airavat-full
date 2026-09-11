# paper/generate_map.py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os

os.makedirs('paper/figures', exist_ok=True)

ZONES = {
    'Z1': {'name': 'Arabian Sea NW',  'lat': (17,23), 'lon': (57,63), 'color': '#EF4444'},
    'Z2': {'name': 'Gulf of Oman',    'lat': (22,27), 'lon': (57,63), 'color': '#F97316'},
    'Z3': {'name': 'Lakshadweep Sea', 'lat': (8,15),  'lon': (71,78), 'color': '#1D9E75'},
    'Z4': {'name': 'Bay of Bengal N', 'lat': (15,22), 'lon': (83,89), 'color': '#7F77DD'},
    'Z5': {'name': 'Sri Lanka Coast', 'lat': (5,12),  'lon': (78,85), 'color': '#FBBF24'},
    'Z6': {'name': 'Malabar Coast',   'lat': (8,15),  'lon': (73,79), 'color': '#9FE1CB'},
    'Z7': {'name': 'Andaman Sea',     'lat': (8,16),  'lon': (93,100),'color': '#EC4899'},
}

fig = plt.figure(figsize=(14, 10))
fig.patch.set_facecolor('#0D1117')
ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
ax.set_extent([45, 110, 0, 32], crs=ccrs.PlateCarree())
ax.set_facecolor('#0D2137')

ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor='#0D2137', zorder=0)
ax.add_feature(cfeature.LAND.with_scale('50m'),  facecolor='#1C2128', zorder=1)
ax.add_feature(cfeature.COASTLINE.with_scale('50m'), edgecolor='#30363D', linewidth=0.8, zorder=2)
ax.add_feature(cfeature.BORDERS.with_scale('50m'),   edgecolor='#21262D', linewidth=0.5, zorder=2)

gl = ax.gridlines(draw_labels=False, linewidth=0.4, color='#30363D', alpha=0.6, linestyle='--')
gl.xlocator = mticker.FixedLocator(range(45, 115, 10))
gl.ylocator = mticker.FixedLocator(range(0, 35, 5))

for lon in range(50, 110, 10):
    ax.text(lon, -0.8, f'{lon}°E', transform=ccrs.PlateCarree(),
            color='#8B949E', fontsize=8, ha='center', va='top')
for lat in range(5, 32, 5):
    ax.text(44.5, lat, f'{lat}°N', transform=ccrs.PlateCarree(),
            color='#8B949E', fontsize=8, ha='right', va='center')

for zid, z in ZONES.items():
    lat1, lat2 = z['lat']
    lon1, lon2 = z['lon']
    color = z['color']
    rect = mpatches.Rectangle(
        (lon1, lat1), lon2-lon1, lat2-lat1,
        linewidth=2, edgecolor=color, facecolor=color,
        alpha=0.25, transform=ccrs.PlateCarree(), zorder=3
    )
    ax.add_patch(rect)
    cx, cy = (lon1+lon2)/2, (lat1+lat2)/2
    ax.text(cx, cy, zid, transform=ccrs.PlateCarree(),
            color='white', fontsize=11, fontweight='bold',
            ha='center', va='center', zorder=5,
            bbox=dict(boxstyle='round,pad=0.2', facecolor=color,
                      alpha=0.85, edgecolor='none'))

legend_elements = [
    mpatches.Patch(facecolor=z['color'], alpha=0.75,
                   label=f"{zid} — {z['name']}")
    for zid, z in ZONES.items()
]
legend = ax.legend(handles=legend_elements, loc='lower left',
                    fontsize=9, facecolor='#161B22',
                    edgecolor='#30363D', labelcolor='#E6EDF3',
                    title='AIRAVAT Monitoring Zones', title_fontsize=9)
legend.get_title().set_color('#9FE1CB')

for name, lon, lat in [
    ('India', 78, 20), ('Arabian\nSea', 63, 13),
    ('Bay of\nBengal', 88, 13), ('Sri Lanka', 81, 7),
    ('Oman', 57, 22), ('Pakistan', 67, 27),
    ('Andaman\nSea', 95, 12),
]:
    ax.text(lon, lat, name, transform=ccrs.PlateCarree(),
            color='#8B949E', fontsize=8, ha='center',
            style='italic', zorder=4)

ax.set_title(
    'AIRAVAT 3.0 — Indian Ocean Monitoring Zones\n'
    'NASA MUR SST (1 km) + Copernicus OLCI Chl-$a$ (4 km)',
    color='#E6EDF3', fontsize=13, pad=14
)

plt.tight_layout()
plt.savefig('paper/figures/fig1_map.pdf', dpi=300, bbox_inches='tight', facecolor='#0D1117')
plt.savefig('paper/figures/fig1_map.png', dpi=300, bbox_inches='tight', facecolor='#0D1117')
print("Fig 1 saved to paper/figures/")
plt.close()