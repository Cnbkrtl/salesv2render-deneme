"""
Sync Control Endpoint
Manuel sync tetikleme ve durum kontrolü
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Dict, Any

from services.scheduled_sync import get_scheduler

router = APIRouter(prefix="/api/sync", tags=["Sync Control"])


@router.post("/trigger/full")
async def trigger_full_sync() -> Dict[str, Any]:
    """
    Manuel tam sync tetikle (tüm veri)
    """
    scheduler = get_scheduler()
    await scheduler.trigger_full_sync_now()
    
    return {
        "status": "triggered",
        "sync_type": "full",
        "message": "Tam veri senkronizasyonu başlatıldı",
        "timestamp": datetime.now()
    }


@router.post("/trigger/live")
async def trigger_live_sync() -> Dict[str, Any]:
    """
    Manuel canlı sync tetikle (sadece bugün)
    """
    scheduler = get_scheduler()
    await scheduler.trigger_live_sync_now()
    
    return {
        "status": "triggered",
        "sync_type": "live",
        "message": "Canlı veri senkronizasyonu başlatıldı",
        "timestamp": datetime.now()
    }


@router.get("/status")
async def get_sync_status() -> Dict[str, Any]:
    """
    Sync durumunu getir
    """
    scheduler = get_scheduler()
    
    return {
        "is_running": scheduler.is_running,
        "last_full_sync": scheduler.last_full_sync.isoformat() if scheduler.last_full_sync else None,
        "last_live_sync": scheduler.last_live_sync.isoformat() if scheduler.last_live_sync else None,
        "full_sync_time": scheduler.full_sync_time.strftime("%H:%M"),
        "live_sync_interval_minutes": scheduler.live_sync_interval // 60,
        "timestamp": datetime.now()
    }
