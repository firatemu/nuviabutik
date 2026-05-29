import os
import sys
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer
from typing import List
from utils.logger import config

EXPECTED_TOKEN = config['security'].get('auth_token', 'NuviaSecretPrintToken2026')
ALLOWED_ORIGINS: List[str] = config['security'].get('allowed_origins', [])

security = HTTPBearer()

async def verify_token(credentials: str = Security(security)):
    if credentials.credentials != EXPECTED_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

def check_origin(request: Request):
    """
    Middleware or dependency to verify Origin/Referer against allowed list.
    FastAPI CORS middleware handles most of this, but we can enforce strictly here.
    """
    origin = request.headers.get("origin")
    if not origin:
        # Allow same-host programmatic calls or strict blockage
        return True
        
    if origin not in ALLOWED_ORIGINS:
        raise HTTPException(
            status_code=403,
            detail=f"Origin {origin} not allowed"
        )
    return True
