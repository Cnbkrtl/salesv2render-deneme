"""
Health Check Endpoint
"""
from fastapi import APIRouter, Depends
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models import HealthResponse
from app.core.config import get_settings
from connectors.sentos_client import SentosAPIClient
from database.connection import engine

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    Sistem sağlığını kontrol eder (Sentos API kontrolü olmadan)
    """
    settings = get_settings()
    
    # Sentos API check - sadece config'in varlığını kontrol et, API çağrısı yapma
    sentos_connection = "configured" if settings.sentos_api_url and settings.sentos_api_key else "not_configured"
    
    # Database check
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        db_connection = "connected"
    except Exception as e:
        db_connection = "disconnected"
    
    overall_status = "healthy" if db_connection == "connected" else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(),
        sentos_connection=sentos_connection,
        database_connection=db_connection,
        version=settings.app_version
    )
