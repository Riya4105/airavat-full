# esg_engine/dtw_matcher.py
# DTW-based signature matcher
# Compares real zone observations against crisis signature templates
# Returns best match, confidence score, and chain position

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import psycopg2
from datetime import datetime, timedelta, timezone
from dtaidistance import dtw
from esg_engine.signatures import SIGNATURES, get_signature_names, get_signature_array
from config.zones import ZONES

import os
from urllib.parse import urlparse

def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        parsed = urlparse(db_url)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            sslmode="require"
        )
    else:
        return psycopg2.connect(
            host="localhost", port=5432,
            database="airavat", user="airavat",
            password="airavat123"
        )

def get_recent_observations(conn, zone_id, days=14):
    """
    Fetches last N days of SST and Chl-a for a zone.
    Returns list of (sst, chl_a) tuples ordered by time.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    cur = conn.cursor()
    cur.execute("""
        SELECT sst, chl_a
        FROM zone_observations
        WHERE zone_id = %s
          AND time >= %s
          AND sst IS NOT NULL
          AND chl_a IS NOT NULL
        ORDER BY time ASC;
    """, (zone_id, cutoff))
    rows = cur.fetchall()
    cur.close()
    return rows

def get_zone_baseline(conn, zone_id):
    """Fetches mean/std baseline for a zone."""
    cur = conn.cursor()
    cur.execute("""
        SELECT mean_sst, std_sst, mean_chl_a, std_chl_a
        FROM zone_baselines
        WHERE zone_id = %s;
    """, (zone_id,))
    row = cur.fetchone()
    cur.close()
    return row  # (mean_sst, std_sst, mean_chl_a, std_chl_a)

def normalise_observations(obs, baseline):
    """
    Converts raw observations to anomaly values
    (deviation from zone baseline in units of std dev).
    """
    mean_sst, std_sst, mean_chl, std_chl = baseline

    sst_anomalies = []
    chl_anomalies = []

    for sst, chl in obs:
        # Anomaly = (observed - mean) — keep in raw °C / mg/m³ for DTW
        sst_anomalies.append(sst - mean_sst)
        chl_anomalies.append(chl - mean_chl)

    return np.array(sst_anomalies), np.array(chl_anomalies)

def match_signature(sst_anomalies, chl_anomalies, event_type):
    """
    Computes multivariate DTW distance between observed anomalies
    and a crisis signature template using both SST and Chl-a.
    Returns confidence score 0-1 (1 = perfect match).
    """
    sig_sst = get_signature_array(event_type, "sst")
    sig_chl = get_signature_array(event_type, "chl")
    sig_len = len(sig_sst)

    # Trim observed series to signature length
    obs_sst = sst_anomalies[-sig_len:] if len(sst_anomalies) >= sig_len \
              else np.pad(sst_anomalies, (sig_len - len(sst_anomalies), 0))
    obs_chl = chl_anomalies[-sig_len:] if len(chl_anomalies) >= sig_len \
              else np.pad(chl_anomalies, (sig_len - len(chl_anomalies), 0))

    try:
        # Individual DTW distances per signal
        dist_sst = dtw.distance(
            obs_sst.astype(np.double),
            sig_sst.astype(np.double)
        )
        dist_chl = dtw.distance(
            obs_chl.astype(np.double),
            sig_chl.astype(np.double)
        )

        # Multivariate combined distance
        # SST weighted 60%, Chl-a weighted 40%
        # Normalise each by their signature magnitude to equalise scales
        sst_scale = max(np.std(sig_sst), 0.01)
        chl_scale = max(np.std(sig_chl), 0.01)

        norm_sst = dist_sst / sst_scale
        norm_chl = dist_chl / chl_scale

        combined = 0.6 * norm_sst + 0.4 * norm_chl

    except Exception:
        return 0.0

    # Convert distance to confidence
    confidence = 1.0 / (1.0 + combined)
    return round(float(confidence), 4)

def detect_chain_position(sst_anomalies, event_type):
    """
    Estimates how far along the crisis chain the zone currently is.
    Returns step number (1-indexed) and description.
    """
    sig = SIGNATURES[event_type]
    sig_sst = np.array(sig["sst"])
    n_steps = sig["steps"]

    if len(sst_anomalies) == 0:
        return 1, sig["description"][0]

    current_anomaly = float(sst_anomalies[-1])

    # Find which step the current anomaly most closely matches
    distances = [abs(current_anomaly - s) for s in sig_sst]
    best_step = int(np.argmin(distances))

    step_num = best_step + 1  # 1-indexed
    description = sig["description"][best_step]

    return step_num, description

def run_dtw_for_zone(zone_id):
    """
    Runs full DTW analysis for a single zone.
    Returns dict with best match, confidence, chain position.
    """
    conn = get_db()

    obs = get_recent_observations(conn, zone_id, days=14)
    baseline = get_zone_baseline(conn, zone_id)

    if not obs or not baseline or len(obs) < 3:
        conn.close()
        return {
            "zone_id": zone_id,
            "status": "insufficient_data",
            "best_match": "normal",
            "confidence": 0.0,
            "chain_position": 1,
            "chain_description": "Insufficient data",
            "alert_level": "NORMAL"
        }

    sst_anom, chl_anom = normalise_observations(obs, baseline)

    # Match against all crisis signatures
    scores = {}
    for event_type in get_signature_names():
        scores[event_type] = match_signature(sst_anom, chl_anom, event_type)

    # Best match
    best_event = max(scores, key=scores.get)
    best_confidence = scores[best_event]

    # Chain position
    chain_pos, chain_desc = detect_chain_position(sst_anom, best_event)

    # Historical similarity (z-score of latest SST anomaly)
    mean_sst, std_sst = baseline[0], baseline[1]
    latest_sst = obs[-1][0]
    hist_sim = 1.0 - min(abs(latest_sst - mean_sst) / (std_sst + 0.001), 1.0)

    # Slope score — is SST trending in the signature direction?
    if len(sst_anom) >= 3:
        slope = float(np.polyfit(range(len(sst_anom[-3:])),
                                  sst_anom[-3:], 1)[0])
        slope_score = min(abs(slope) / 0.5, 1.0)
    else:
        slope_score = 0.0

    # Convergence score
    priority = (0.4 * best_confidence +
                0.35 * (1 - hist_sim) +
                0.25 * slope_score)
    priority = round(priority, 4)

    # Alert level
    if priority >= 0.55:
        alert_level = "HIGH"
    elif priority >= 0.35:
        alert_level = "WARN"
    else:
        alert_level = "NORMAL"

    conn.close()

    return {
        "zone_id":           zone_id,
        "zone_name":         ZONES[zone_id]["name"],
        "best_match":        best_event,
        "confidence":        best_confidence,
        "all_scores":        scores,
        "chain_position":    chain_pos,
        "chain_total":       SIGNATURES[best_event]["steps"],
        "chain_description": chain_desc,
        "hist_sim":          round(hist_sim, 4),
        "slope_score":       round(slope_score, 4),
        "priority":          priority,
        "alert_level":       alert_level,
        "latest_sst":        obs[-1][0],
        "latest_chl":        obs[-1][1],
        "obs_count":         len(obs),
    }

def run_all_zones():
    """Runs DTW analysis for all 7 zones and returns ranked results."""
    results = []
    for zone_id in ZONES.keys():
        r = run_dtw_for_zone(zone_id)
        results.append(r)

    # Sort by priority score descending
    results.sort(key=lambda x: x["priority"], reverse=True)
    return results