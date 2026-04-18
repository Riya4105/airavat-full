# config/zones.py
# Bounding boxes for all 7 Indian Ocean monitoring zones
# Format: (lon_min, lat_min, lon_max, lat_max)

ZONES = {
    "Z1": {
        "name": "Arabian Sea NW",
        "bbox": (55, 15, 65, 25),
        "base_sst": 27.0,
        "trend": 0.28,
    },
    "Z2": {
        "name": "Gulf of Oman",
        "bbox": (56, 22, 65, 27),
        "base_sst": 26.5,
        "trend": 0.22,
    },
    "Z3": {
        "name": "Lakshadweep Sea",
        "bbox": (72, 8, 77, 15),
        "base_sst": 28.5,
        "trend": 0.18,
    },
    "Z4": {
        "name": "Bay of Bengal N",
        "bbox": (80, 15, 92, 22),
        "base_sst": 27.5,
        "trend": 0.20,
    },
    "Z5": {
        "name": "Sri Lanka Coast",
        "bbox": (78, 5, 85, 12),
        "base_sst": 29.5,
        "trend": -0.22,
    },
    "Z6": {
        "name": "Malabar Coast",
        "bbox": (74, 8, 78, 15),
        "base_sst": 26.8,
        "trend": 0.38,
    },
    "Z7": {
        "name": "Andaman Sea",
        "bbox": (94, 8, 100, 16),
        "base_sst": 28.2,
        "trend": 0.15,
    },
}