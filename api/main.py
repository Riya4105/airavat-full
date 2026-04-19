# api/main.py
# AIRAVAT 3.0 — Full Product FastAPI Backend

from dotenv import load_dotenv
load_dotenv()

import sys
import os
import json
import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from esg_engine.dtw_matcher import run_all_zones, run_dtw_for_zone
from api.models import FeedbackRequest, QueryRequest
from api.auth import verify_password, create_token, get_current_agency, require_admin, AGENCIES
from config.zones import ZONES

from api.alerts import dispatch_alert, format_alert_message

app = FastAPI(
    title="AIRAVAT 3.0",
    description="AI-Powered Marine Environmental Sentinel — Full Product API",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Database ───────────────────────────────────────────────
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

# ── WebSocket ──────────────────────────────────────────────
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

async def broadcast_zones():
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

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_zones())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        results = run_all_zones()
        await websocket.send_json({
            "type": "zone_update",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "zones": results
        })
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ── Health check ───────────────────────────────────────────
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

# ── Auth endpoints ─────────────────────────────────────────
@app.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    agency_id = form.username
    if agency_id not in AGENCIES:
        raise HTTPException(status_code=401, detail="Agency not found")
    if not verify_password(form.password, agency_id):
        raise HTTPException(status_code=401, detail="Incorrect password")
    token = create_token(agency_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "agency": AGENCIES[agency_id]["name"],
        "zones": AGENCIES[agency_id]["zones"],
        "role": AGENCIES[agency_id]["role"]
    }

@app.get("/auth/me")
def get_me(agency: dict = Depends(get_current_agency)):
    return {
        "agency_id": agency["sub"],
        "name": agency["name"],
        "zones": agency["zones"],
        "role": agency["role"]
    }

# ── Zone endpoints ─────────────────────────────────────────
@app.get("/zones/secure")
def get_zones_secure(agency: dict = Depends(get_current_agency)):
    try:
        all_results = run_all_zones()
        assigned = agency.get("zones", [])
        filtered = [z for z in all_results if z["zone_id"] in assigned]
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agency": agency["name"],
            "zones": filtered
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/zones")
def get_all_zones():
    try:
        results = run_all_zones()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "zones": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/zones/{zone_id}")
def get_zone(zone_id: str):
    zone_id = zone_id.upper()
    if zone_id not in ZONES:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")
    try:
        return run_dtw_for_zone(zone_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Baseline ───────────────────────────────────────────────
@app.get("/baseline")
def get_baselines():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT zone_id, mean_sst, std_sst, mean_chl_a, std_chl_a, last_updated
            FROM zone_baselines ORDER BY zone_id;
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

# ── History ────────────────────────────────────────────────
@app.get("/history/{zone_id}")
def get_history(zone_id: str, days: int = 30):
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
                {"time": r[0].isoformat(), "sst": r[1], "chl_a": r[2], "source": r[3]}
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Feedback ───────────────────────────────────────────────
@app.post("/feedback")
def post_feedback(req: FeedbackRequest):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO zone_alerts (time, zone_id, alert_level, event_type, operator_feedback)
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

@app.get("/feedback")
def get_feedback(zone_id: str = None):
    try:
        conn = get_db()
        cur = conn.cursor()
        if zone_id:
            cur.execute("""
                SELECT time, zone_id, alert_level, event_type, operator_feedback
                FROM zone_alerts WHERE zone_id = %s
                ORDER BY time DESC LIMIT 50;
            """, (zone_id.upper(),))
        else:
            cur.execute("""
                SELECT time, zone_id, alert_level, event_type, operator_feedback
                FROM zone_alerts ORDER BY time DESC LIMIT 50;
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
                    "time": r[0].isoformat(), "zone_id": r[1],
                    "alert_level": r[2], "event_type": r[3], "feedback": r[4]
                }
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ── POST /alert/dispatch ───────────────────────────────────
@app.post("/alert/dispatch")
def dispatch_zone_alert(
    zone_id: str,
    channel: str = "sms",
    agency: dict = Depends(get_current_agency)
):
    """
    Manually dispatch an alert for a zone to agency operators.
    Requires authentication. channel = 'sms' or 'whatsapp'
    """
    zone_id = zone_id.upper()
    if zone_id not in ZONES:
        raise HTTPException(status_code=404, detail=f"Zone {zone_id} not found")
    if zone_id not in agency.get("zones", []):
        raise HTTPException(status_code=403, detail="Zone not assigned to your agency")

    try:
        zone_data = run_dtw_for_zone(zone_id)
        results = dispatch_alert(zone_data, agency["sub"], channel)
        return {
            "status": "dispatched",
            "zone_id": zone_id,
            "zone_name": zone_data["zone_name"],
            "alert_level": zone_data["alert_level"],
            "channel": channel,
            "results": results,
            "message": format_alert_message(zone_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── POST /alert/auto ───────────────────────────────────────
@app.post("/alert/auto")
def auto_dispatch_high_alerts(agency: dict = Depends(require_admin)):
    """
    Admin only — scans all zones and dispatches alerts
    for any zone currently at HIGH alert level.
    """
    try:
        all_zones = run_all_zones()
        high_zones = [z for z in all_zones if z["alert_level"] == "HIGH"]
        dispatched = []

        for zone in high_zones:
            results = dispatch_alert(zone, agency["sub"], "sms")
            dispatched.append({
                "zone_id": zone["zone_id"],
                "zone_name": zone["zone_name"],
                "priority": zone["priority"],
                "results": results
            })

        return {
            "status": "complete",
            "high_zones_found": len(high_zones),
            "dispatched": dispatched
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── NL Query ───────────────────────────────────────────────
@app.post("/query")
def natural_language_query(req: QueryRequest):
    try:
        zone_data = run_all_zones()
        zone_summary = "\n".join([
            f"- {z['zone_name']}: {z['alert_level']} alert, "
            f"{z['best_match']} at step {z['chain_position']}/{z['chain_total']}, "
            f"priority {z['priority']}, SST {z['latest_sst']}C, Chl-a {z['latest_chl']} mg/m3"
            for z in zone_data
        ])

        prompt = f"""You are AIRAVAT 3.0, an AI marine environmental sentinel monitoring the Indian Ocean.
Current zone status:
{zone_summary}
Operator question: {req.question}
Respond in this exact format:
SEVERITY: [HIGH/WARN/NORMAL]
CHAIN STATE: [event type - step X of Y - description]
EXPLANATION: [2-3 sentences]
ACTION: [specific recommended action]"""

        groq_key = os.environ.get("GROQ_API_KEY", "")
        if not groq_key:
            top = zone_data[0]
            return {
                "question": req.question,
                "severity": top["alert_level"],
                "chain_state": f"{top['best_match']} - step {top['chain_position']} of {top['chain_total']}",
                "explanation": f"{top['zone_name']} has the highest priority score of {top['priority']}.",
                "action": "Monitor closely and review chain progression.",
                "source": "rule_based"
            }

        import urllib.request
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

        parsed = {}
        for line in answer.strip().split("\n"):
            if line.startswith("SEVERITY:"):
                parsed["severity"] = line.replace("SEVERITY:", "").strip()
            elif line.startswith("CHAIN STATE:"):
                parsed["chain_state"] = line.replace("CHAIN STATE:", "").strip()
            elif line.startswith("EXPLANATION:"):
                parsed["explanation"] = line.replace("EXPLANATION:", "").strip()
            elif line.startswith("ACTION:"):
                parsed["action"] = line.replace("ACTION:", "").strip()

        return {"question": req.question, **parsed, "source": "groq_llama"}

    except Exception as e:
        import traceback
        print(f"Query error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))