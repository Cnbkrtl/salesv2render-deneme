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
    Sistem sağlığını kontrol eder
    """
    settings = get_settings()
    
    # Sentos API check
    sentos = SentosAPIClient(
        api_url=settings.sentos_api_url,
        api_key=settings.sentos_api_key,
        api_secret=settings.sentos_api_secret
    )
    sentos_status = sentos.test_connection()
    sentos_connection = "connected" if sentos_status['success'] else "disconnected"
    
    # Database check
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        db_connection = "connected"
    except:
        db_connection = "disconnected"
    
    overall_status = "healthy" if (sentos_connection == "connected" and db_connection == "connected") else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(),
        sentos_connection=sentos_connection,
        database_connection=db_connection,
        version=settings.app_version
    )
