# AIRAVAT 3.0 — AI-Powered Marine Environmental Sentinel

> Real-time ecological stress detection for the Indian Ocean using satellite remote sensing, dynamic time warping, and variational autoencoders.

**Live system:** https://riya4105.github.io/airavat-full/  
**API:** https://airavat-full.onrender.com  
**Team:** Thalassa Minds

---

## What is AIRAVAT?

AIRAVAT (Automated Intelligent Remote-sensing for Aquatic Vitality and Threat) is a production marine environmental monitoring system that continuously watches 7 critical Indian Ocean zones for ecological stress events — thermal bleaching, hypoxic blooms, turbidity spikes, upwelling events, and oil slick precursors.

Unlike conventional threshold-based alert systems, AIRAVAT detects **precursor chains** — the multi-step signature patterns that precede a crisis — giving coastal agencies 3-7 days of advance warning before conditions become critical.

---

## Architecture

```
NASA MUR SST (1km daily)          Copernicus Chl-a (4km, 8-day lag)
        │                                      │
        └──────────────┬───────────────────────┘
                       │
              Daily Ingestion Pipeline
                       │
              Railway PostgreSQL
              (630+ observations, 7 zones)
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   Zone Baselines   DTW Engine    VAE Encoder
   (90-day mean     (6 crisis     (latent zone
    per zone)        signatures)   personality)
        │              │              │
        └──────────────┼──────────────┘
                       │
              Convergence Score
              priority = 0.4×DTW + 0.35×VAE + 0.25×slope
                       │
              ┌────────┴────────┐
           HIGH ≥0.55        WARN ≥0.35
              │
        Twilio SMS + WhatsApp
        (auto-dispatch to agencies)
                       │
              FastAPI Backend
              (JWT multi-agency auth)
                       │
              GitHub Pages Frontend
              (Leaflet.js + Chart.js)
```

---

## Three Core Differentiators

### 1. Zone Personality Baselines
Each of the 7 zones has a 90-day learned baseline computed from real NASA MUR SST and Copernicus Chl-a satellite observations. Anomaly detection is relative to each zone's own historical distribution — not a global threshold. Arabian Sea NW and Bay of Bengal N have fundamentally different normal conditions; AIRAVAT accounts for this.

### 2. ESG Precursor Chain Detection
Six crisis signature templates are encoded as multivariate time-series patterns:

| Event | SST pattern | Chl-a pattern | Steps |
|---|---|---|---|
| Thermal stress | +0.2 → +3.5°C over 7 steps | Gradual suppression | 7 |
| Hypoxic bloom | Slight warming | +0.3 → +5.0 mg/m³ over 7 steps | 7 |
| Turbidity spike | Cooling (-0.2 → -0.4°C) | Sharp Chl-a spike | 6 |
| Upwelling | Cooling (-0.3 → -1.5°C) | Productivity increase | 6 |
| Oil slick | Slight warming | Progressive suppression | 7 |
| Normal | Stable | Stable | 3 |

Dynamic Time Warping (DTW) matches real observations against these templates with 60% SST / 40% Chl-a weighting, normalised by signal magnitude to equalise scales.

### 3. VAE Zone Encoder
A Variational Autoencoder trained on 90 days of real satellite data per zone learns each zone's latent personality as an 8-dimensional vector. Reconstruction error on new observations gives a continuous anomaly score independent of the DTW matching — a second line of evidence that converges with DTW for high-confidence alerts.

---

## Monitored Zones

| Zone | Name | Coverage |
|---|---|---|
| Z1 | Arabian Sea NW | 17-23°N, 57-63°E |
| Z2 | Gulf of Oman | 22-27°N, 57-63°E |
| Z3 | Lakshadweep Sea | 8-15°N, 71-78°E |
| Z4 | Bay of Bengal N | 15-22°N, 83-89°E |
| Z5 | Sri Lanka Coast | 5-12°N, 78-85°E |
| Z6 | Malabar Coast | 8-15°N, 73-79°E |
| Z7 | Andaman Sea | 8-16°N, 93-100°E |

---

## Data Sources

| Source | Variable | Resolution | Latency |
|---|---|---|---|
| NASA MUR JPL L4 (v4.1) | Sea Surface Temperature | 1km daily | ~1 day |
| Copernicus OLCI MY L4 | Chlorophyll-a | 4km daily | ~8 days |

Both datasets are accessed via authenticated APIs — NASA Earthdata (`earthaccess`) and Copernicus Marine Service (`copernicusmarine`).

---

## Multi-Agency Access Control

AIRAVAT uses JWT authentication with role-based zone filtering. Different agencies see only their assigned zones:

| Agency | Role | Zones |
|---|---|---|
| Indian Coast Guard | Admin | All 7 zones |
| Kerala Fisheries Dept | Operator | Z3, Z6 |
| Indian Ocean Conservation NGO | Observer | Z3, Z5, Z7 |
| Thalassa Minds Admin | Admin | All 7 zones |

---

## Alert Pipeline

```
Scheduler (every 30 min)
    → Run ESG engine on all zones
    → Find zones at HIGH (priority ≥ 0.55)
    → For each HIGH zone:
        → Identify agencies with that zone assigned
        → Dispatch SMS via Twilio
        → Dispatch WhatsApp via Twilio sandbox
        → Log to zone_alerts table
        → Track alerted zones (no duplicate SMS until recovery)
    → When zone drops to WARN/NORMAL:
        → Clear tracking → re-enables future alerts
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data ingestion | Python, earthaccess, copernicusmarine |
| Time-series DB | Railway PostgreSQL (TimescaleDB locally) |
| DTW engine | dtaidistance |
| VAE encoder | PyTorch (CPU) |
| API | FastAPI, Uvicorn |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Alerts | Twilio (SMS + WhatsApp) |
| Frontend | Leaflet.js, Chart.js, vanilla JS |
| Hosting | Render (API), GitHub Pages (frontend) |
| Scheduler | Python schedule |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/zones` | All zones ranked by ESG priority |
| GET | `/zones/{id}` | Single zone with VAE anomaly score |
| GET | `/zones/secure` | JWT-filtered zones for current agency |
| GET | `/baseline` | Zone personality baselines |
| GET | `/history/{id}` | Raw observation history |
| POST | `/auth/login` | Agency login → JWT token |
| GET | `/auth/me` | Current agency info |
| POST | `/feedback` | Operator feedback (one per zone per alert level) |
| GET | `/feedback` | Feedback history + accuracy metrics |
| POST | `/query` | Natural language marine intelligence query |
| POST | `/alert/dispatch` | Manual alert dispatch |
| POST | `/alert/auto` | Admin: auto-dispatch all HIGH zones |
| WS | `/ws` | WebSocket live zone updates |

---

## Local Setup

```bash
# Clone
git clone https://github.com/Riya4105/airavat-full
cd airavat-full

# Virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Fill in: GROQ_API_KEY, TWILIO_*, DATABASE_URL

# Start local TimescaleDB
docker run -d --name airavat-timescaledb \
  -e POSTGRES_PASSWORD=airavat123 \
  -e POSTGRES_USER=airavat \
  -e POSTGRES_DB=airavat \
  -p 5432:5432 \
  timescale/timescaledb:latest-pg16

# Setup database
python test_db.py

# Run backfill (90 days of satellite data — takes 2-3 hours)
python ingestion/backfill.py

# Compute zone baselines
python ingestion/compute_baselines.py

# Train VAE encoders
python esg_engine/vae_encoder.py

# Start API server
uvicorn api.main:app --port 8000 --reload

# Start scheduler (separate terminal)
python scheduler.py

# Serve frontend
python -m http.server 3000 --directory frontend
```

---

## Daily Maintenance

```bash
# Fetch latest satellite data (run daily)
python ingestion/daily_ingest.py
python ingestion/compute_baselines.py

# Retrain VAE monthly as data accumulates
python esg_engine/vae_encoder.py
```

---

## Repository Structure

```
airavat-full/
├── config/
│   └── zones.py              # Zone definitions and bounding boxes
├── ingestion/
│   ├── nasa_sst.py           # NASA MUR SST fetcher
│   ├── copernicus_chl.py     # Copernicus Chl-a fetcher
│   ├── daily_ingest.py       # Combined daily ingestion
│   ├── backfill.py           # 90-day historical backfill
│   └── compute_baselines.py  # Zone personality baseline calculator
├── esg_engine/
│   ├── signatures.py         # 6 crisis signature templates
│   ├── dtw_matcher.py        # Multivariate DTW matching engine
│   └── vae_encoder.py        # VAE zone personality encoder
├── api/
│   ├── main.py               # FastAPI application
│   ├── models.py             # Pydantic request/response models
│   ├── auth.py               # JWT authentication
│   └── alerts.py             # Twilio SMS + WhatsApp dispatch
├── data/
│   └── models/               # Trained VAE weights (Z1-Z7)
├── frontend/
│   ├── index.html            # Main application
│   ├── app.js                # Frontend logic
│   └── style.css             # Dark theme styling
├── scheduler.py              # Auto-ingestion + auto-alert scheduler
├── keep_alive.py             # Render cold-start prevention
└── requirements.txt
```

---

## Adaptive Learning

Operator feedback directly improves system accuracy. Each confirmation or false-positive report is logged per zone per alert level. The adaptive learning bar in the UI tracks:

- **True Positives (TP):** Confirmed alerts
- **False Positives (FP):** Rejected alerts  
- **Accuracy:** TP / (TP + FP)

This data can be used to fine-tune DTW signature weights and VAE reconstruction thresholds in future versions.

---

## Research Directions

- **GNN spatial propagation:** Model crisis signals propagating between adjacent zones as a graph
- **Longer VAE training:** As data accumulates beyond 6 months, VAE latent vectors will capture seasonal cycles
- **Multi-variable expansion:** Add salinity, wind speed, and sea level anomaly as additional ESG signals
- **Coral bleaching degree heating weeks:** Integrate NOAA DHW product for direct bleaching risk correlation

---

## License

MIT License — see LICENSE file.

---

*Built by Thalassa Minds. Data from NASA Earthdata and Copernicus Marine Service.*
