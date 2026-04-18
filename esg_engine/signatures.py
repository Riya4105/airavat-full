# esg_engine/signatures.py
# Crisis signature templates — 6 event types
# Each template is a normalised multi-step pattern for SST and Chl-a
# Built from published Indian Ocean case studies + synthetic simulations

import numpy as np

# Each signature is a dict with:
#   "sst"   : list of relative SST changes per step (°C delta from baseline)
#   "chl"   : list of relative Chl-a changes per step (mg/m³ delta from baseline)
#   "steps" : total number of steps in the chain
#   "description": what this crisis looks like at each step

SIGNATURES = {

    "thermal_stress": {
        "steps": 7,
        "sst":  [0.2, 0.5, 0.9, 1.4, 2.0, 2.8, 3.5],
        "chl":  [0.0, 0.0, -0.05, -0.1, -0.15, -0.2, -0.3],
        "description": [
            "Slight SST rise — within normal variation",
            "SST trending upward — 2 consecutive days",
            "SST anomaly confirmed — Chl-a beginning to drop",
            "Thermal stress building — bleaching risk zone",
            "High thermal stress — coral bleaching likely",
            "Severe thermal stress — mass bleaching event",
            "Crisis — ecosystem collapse risk",
        ]
    },

    "hypoxic_bloom": {
        "steps": 7,
        "sst":  [0.1, 0.2, 0.3, 0.2, 0.1, 0.0, -0.1],
        "chl":  [0.3, 0.8, 1.5, 2.5, 3.5, 4.5, 5.0],
        "description": [
            "Minor Chl-a elevation — early phytoplankton growth",
            "Chl-a rising — nutrient upwelling suspected",
            "Bloom forming — Chl-a significantly elevated",
            "Dense bloom — oxygen depletion beginning",
            "Hypoxic conditions — marine life stress",
            "Severe hypoxia — fish kill risk",
            "Crisis — widespread hypoxic zone",
        ]
    },

    "turbidity_spike": {
        "steps": 6,
        "sst":  [-0.2, -0.3, -0.4, -0.3, -0.2, -0.1],
        "chl":  [0.5,  1.0,  1.8,  2.2,  2.5,  2.0],
        "description": [
            "SST drop — possible upwelling or runoff",
            "Turbidity rising — sediment or algae influx",
            "High turbidity — light penetration reduced",
            "Peak turbidity — ecosystem stress",
            "Turbidity declining but Chl-a elevated",
            "Recovery phase — monitoring required",
        ]
    },

    "upwelling": {
        "steps": 6,
        "sst":  [-0.3, -0.7, -1.2, -1.5, -1.3, -1.0],
        "chl":  [0.2,  0.6,  1.2,  1.8,  2.2,  1.8],
        "description": [
            "SST cooling — upwelling initiating",
            "Cold water rising — nutrient injection",
            "Strong upwelling — surface SST significantly cool",
            "Peak upwelling — high productivity zone",
            "Upwelling moderating — bloom sustained",
            "Post-upwelling bloom — fisheries opportunity",
        ]
    },

    "oil_slick": {
        "steps": 7,
        "sst":  [0.1, 0.2, 0.3, 0.4, 0.3, 0.2, 0.1],
        "chl":  [-0.1, -0.2, -0.4, -0.6, -0.7, -0.8, -0.9],
        "description": [
            "Minor surface anomaly detected",
            "SST slightly elevated — surface film suspected",
            "Chl-a suppression confirmed — light blockage",
            "Significant Chl-a drop — oil slick likely",
            "Severe phytoplankton suppression",
            "Ecosystem impact — food chain disruption",
            "Crisis — widespread contamination",
        ]
    },

    "normal": {
        "steps": 3,
        "sst":  [0.0, 0.0, 0.0],
        "chl":  [0.0, 0.0, 0.0],
        "description": [
            "Normal conditions",
            "Normal conditions",
            "Normal conditions",
        ]
    },
}

def get_signature_names():
    return [k for k in SIGNATURES.keys() if k != "normal"]

def get_signature_array(event_type, signal="sst"):
    """Returns signature as numpy array for DTW matching."""
    return np.array(SIGNATURES[event_type][signal])