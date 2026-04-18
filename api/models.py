# api/models.py
# Pydantic models for request/response validation

from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class ZoneScore(BaseModel):
    zone_id: str
    zone_name: str
    best_match: str
    confidence: float
    chain_position: int
    chain_total: int
    chain_description: str
    priority: float
    alert_level: str
    latest_sst: float
    latest_chl: float
    hist_sim: float
    slope_score: float
    obs_count: int

class AllZonesResponse(BaseModel):
    timestamp: str
    zones: list[ZoneScore]

class FeedbackRequest(BaseModel):
    zone_id: str
    alert_level: str
    event_type: str
    feedback: str  # "confirm" or "false_positive"
    operator: Optional[str] = "anonymous"

class QueryRequest(BaseModel):
    question: str
    zone_id: Optional[str] = None