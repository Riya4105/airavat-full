# api/main.py
# AIRAVAT 3.0 — Full Product FastAPI Backend
# Endpoints:
#   GET  /              health check
#   GET  /zones         all 7 zones ESG scores ranked
#   GET  /zones/{id}    single zone detail
#   GET  /baseline      all zone baselines
#   POST /query         natural language query via Groq
#   POST /feedback      operator feedback logging
#   GET  /feedback      retrieve feedback history
from dotenv import load_dotenv
load_dotenv()
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import psycopg2
import json
import os

from esg_engine.dtw_matcher import run_all_zones, run_dtw_for_zone
from api.models import FeedbackRequest, QueryRequest
from config.zones import ZONES

from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import asyncio

app = FastAPI(
    title="AIRAVAT 3.0",
    description="AI-Powered Marine Environmental Sentinel — Full Product API",
    version="3.0.0"
)

# Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    
# ── WebSocket Connection Manager ──────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()

# ── Background zone broadcaster ────────────────────────────
async def broadcast_zones():
    """Pushes zone updates to all connected clients every 30 seconds."""
    while True:
        try:
            if manager.active:
                results = run_all_zones()
                await manager.broadcast({
                    "type": "zone_update",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "zones": results
                })
        except Exception as e:
            print(f"Broadcast error: {e}")
        await asyncio.sleep(30)

# ── Startup event ──────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_zones())

# ── WebSocket endpoint ─────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send current zone data immediately on connect
        results = run_all_zones()
        await websocket.send_json({
            "type": "zone_update",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "zones": results
        })
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ── GET / ─────────────────────────────────────────────────
@app.get("/")
def health():
    return {
        "status": "live",
        "system": "AIRAVAT 3.0",
        "version": "3.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_source": "NASA MUR SST + Copernicus Chl-a",
        "zones": len(ZONES)
    }

# ── GET /zones ────────────────────────────────────────────
@app.get("/zones")
def get_all_zones():
    """Returns all 7 zones ranked by ESG priority score."""
    try:
        results = run_all_zones()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "zones": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── GET /zones/{zone_id} ──────────────────────────────────
@app.get("/zones/{zone_id}")
def get_zone(zone_id: str):
    """Returns detailed ESG analysis for a single zone."""
    zone_id = zone_id.upper()
    if zone_id not in ZONES:
        raise HTTPException(
            status_code=404,
            detail=f"Zone {zone_id} not found. Valid zones: {list(ZONES.keys())}"
        )
    try:
        result = run_dtw_for_zone(zone_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── GET /baseline ─────────────────────────────────────────
@app.get("/baseline")
def get_baselines():
    """Returns zone personality baselines for all zones."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT zone_id, mean_sst, std_sst,
                   mean_chl_a, std_chl_a, last_updated
            FROM zone_baselines
            ORDER BY zone_id;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return {
            "baselines": [
                {
                    "zone_id":      r[0],
                    "zone_name":    ZONES[r[0]]["name"],
                    "mean_sst":     r[1],
                    "std_sst":      r[2],
                    "mean_chl_a":   r[3],
                    "std_chl_a":    r[4],
                    "last_updated": r[5].isoformat() if r[5] else None
                }
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── GET /history/{zone_id} ────────────────────────────────
@app.get("/history/{zone_id}")
def get_history(zone_id: str, days: int = 14):
    """Returns raw observation history for a zone."""
    zone_id = zone_id.upper()
    if zone_id not in ZONES:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT time, sst, chl_a, source
            FROM zone_observations
            WHERE zone_id = %s
              AND time >= NOW() - INTERVAL '%s days'
              AND sst IS NOT NULL
            ORDER BY time ASC;
        """, (zone_id, days))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return {
            "zone_id":   zone_id,
            "zone_name": ZONES[zone_id]["name"],
            "days":      days,
            "observations": [
                {
                    "time":   r[0].isoformat(),
                    "sst":    r[1],
                    "chl_a":  r[2],
                    "source": r[3]
                }
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── POST /feedback ────────────────────────────────────────
@app.post("/feedback")
def post_feedback(req: FeedbackRequest):
    """Logs operator feedback for adaptive learning."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO zone_alerts
                (time, zone_id, alert_level, event_type, operator_feedback)
            VALUES (NOW(), %s, %s, %s, %s);
        """, (req.zone_id, req.alert_level, req.event_type, req.feedback))
        conn.commit()
        cur.close()
        conn.close()

        return {
            "status": "logged",
            "zone_id": req.zone_id,
            "feedback": req.feedback,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── GET /feedback ─────────────────────────────────────────
@app.get("/feedback")
def get_feedback(zone_id: str = None):
    """Retrieves feedback history, optionally filtered by zone."""
    try:
        conn = get_db()
        cur = conn.cursor()
        if zone_id:
            cur.execute("""
                SELECT time, zone_id, alert_level, event_type, operator_feedback
                FROM zone_alerts
                WHERE zone_id = %s
                ORDER BY time DESC LIMIT 50;
            """, (zone_id.upper(),))
        else:
            cur.execute("""
                SELECT time, zone_id, alert_level, event_type, operator_feedback
                FROM zone_alerts
                ORDER BY time DESC LIMIT 50;
            """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        tp = sum(1 for r in rows if r[4] == "confirm")
        fp = sum(1 for r in rows if r[4] == "false_positive")

        return {
            "total": len(rows),
            "true_positives": tp,
            "false_positives": fp,
            "accuracy": round(tp / len(rows), 2) if rows else 0,
            "feedback": [
                {
                    "time":      r[0].isoformat(),
                    "zone_id":   r[1],
                    "alert_level": r[2],
                    "event_type":  r[3],
                    "feedback":    r[4]
                }
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── POST /query ───────────────────────────────────────────
@app.post("/query")
def natural_language_query(req: QueryRequest):
    """
    Accepts a natural language question and returns
    structured marine intelligence using Groq LLaMA.
    """
    try:
        # Get current zone data to give context to the LLM
        zone_data = run_all_zones()

        # Format zone summary for LLM context
        zone_summary = "\n".join([
            f"- {z['zone_name']}: {z['alert_level']} alert, "
            f"{z['best_match']} at step {z['chain_position']}/{z['chain_total']}, "
            f"priority {z['priority']}, SST {z['latest_sst']}°C, "
            f"Chl-a {z['latest_chl']} mg/m³"
            for z in zone_data
        ])

        prompt = f"""You are AIRAVAT 3.0, an AI marine environmental sentinel 
monitoring the Indian Ocean. You have real-time ESG (Ecological Stress Grade) 
data for 7 zones.

Current zone status:
{zone_summary}

Operator question: {req.question}

Respond in this exact format:
SEVERITY: [HIGH/WARN/NORMAL]
CHAIN STATE: [event type — step X of Y — description]
EXPLANATION: [2-3 sentences explaining what is happening and why]
ACTION: [specific recommended action for the operator]"""

        # Call Groq API
        import urllib.request
        groq_key = os.environ.get("GROQ_API_KEY", "")

        if not groq_key:
            # Return structured response without LLM if no key
            top = zone_data[0]
            return {
                "question": req.question,
                "severity": top["alert_level"],
                "chain_state": f"{top['best_match']} — step {top['chain_position']} of {top['chain_total']}",
                "explanation": f"{top['zone_name']} has the highest priority score of {top['priority']}.",
                "action": "Monitor closely and review chain progression.",
                "source": "rule_based"
            }

        payload = json.dumps({
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300
        }).encode("utf-8")

        req_obj = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {groq_key}"
            }
        )

        with urllib.request.urlopen(req_obj) as response:
            data = json.loads(response.read())
            answer = data["choices"][0]["message"]["content"]

        # Parse structured response
        lines = answer.strip().split("\n")
        parsed = {}
        for line in lines:
            if line.startswith("SEVERITY:"):
                parsed["severity"] = line.replace("SEVERITY:", "").strip()
            elif line.startswith("CHAIN STATE:"):
                parsed["chain_state"] = line.replace("CHAIN STATE:", "").strip()
            elif line.startswith("EXPLANATION:"):
                parsed["explanation"] = line.replace("EXPLANATION:", "").strip()
            elif line.startswith("ACTION:"):
                parsed["action"] = line.replace("ACTION:", "").strip()

        return {
            "question": req.question,
            **parsed,
            "source": "groq_llama"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))