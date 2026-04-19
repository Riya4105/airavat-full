# api/auth.py
# JWT authentication for multi-agency access

import os
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = os.environ.get("JWT_SECRET", "airavat-dev-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Agency definitions — in production store in database
AGENCIES = {
    "coast_guard": {
        "name": "Indian Coast Guard",
        "password": "coastguard123",
        "zones": ["Z1","Z2","Z3","Z4","Z5","Z6","Z7"],
        "role": "admin"
    },
    "fisheries_kerala": {
        "name": "Kerala Fisheries Department",
        "password": "fisheries123",
        "zones": ["Z6","Z3"],
        "role": "operator"
    },
    "conservation_ngo": {
        "name": "Indian Ocean Conservation NGO",
        "password": "conservation123",
        "zones": ["Z3","Z5","Z7"],
        "role": "observer"
    },
    "thalassa_admin": {
        "name": "Thalassa Minds Admin",
        "password": "thalassa2026",
        "zones": ["Z1","Z2","Z3","Z4","Z5","Z6","Z7"],
        "role": "admin"
    }
}

def verify_password(plain: str, agency_id: str) -> bool:
    agency = AGENCIES.get(agency_id)
    if not agency:
        return False
    return plain == agency["password"]

def create_token(agency_id: str) -> str:
    agency = AGENCIES[agency_id]
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": agency_id,
        "name": agency["name"],
        "zones": agency["zones"],
        "role": agency["role"],
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

def get_current_agency(token: str = Depends(oauth2_scheme)) -> dict:
    return decode_token(token)

def require_admin(agency: dict = Depends(get_current_agency)) -> dict:
    if agency.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return agency