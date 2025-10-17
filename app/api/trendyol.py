"""
Trendyol API Endpoint
Manuel Trendyol sync tetikleme
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio
import logging

from connectors.trendyol_client import TrendyolAPIClient
from services.trendyol_data_fetcher import TrendyolDataFetcherService
from app.core.config import get_settings

router = APIRouter(prefix="/api/trendyol", tags=["Trendyol"])
logger = logging.getLogger(__name__)


@router.post("/sync")
async def sync_trendyol_orders(
    days: int = Query(default=7, ge=1, le=30, description="Son kaç günün verisi çekilecek (1-30 arası)")
) -> Dict[str, Any]:
    """
    Manuel Trendyol sipariş senkronizasyonu
    
    Args:
        days: Son kaç günün verisi çekilecek (varsayılan: 7)
    
    Returns:
        Sync sonuçları (sipariş sayısı, item sayısı, süre)
    """
    try:
        settings = get_settings()
        
        # Trendyol credentials kontrolü
        if not settings.trendyol_supplier_id or not settings.trendyol_api_secret:
            raise HTTPException(
                status_code=400,
                detail="Trendyol API credentials eksik. TRENDYOL_SUPPLIER_ID ve TRENDYOL_API_SECRET gerekli."
            )
        
        start_time = datetime.now()
        logger.info(f"🟠 Manuel Trendyol sync başlatıldı (son {days} gün)")
        
        # Trendyol client oluştur
        trendyol_client = TrendyolAPIClient(
            supplier_id=settings.trendyol_supplier_id,
            api_key=settings.trendyol_api_key,
            api_secret=settings.trendyol_api_secret
        )
        
        # Trendyol data fetcher oluştur
        trendyol_fetcher = TrendyolDataFetcherService(trendyol_client=trendyol_client)
        
        # Tarih aralığını hesapla
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Veri çek ve kaydet
        result = await asyncio.to_thread(
            trendyol_fetcher.fetch_and_store_trendyol_orders,
            start_date=start_date,
            end_date=end_date,
            statuses=None  # Tüm statusler
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ Trendyol sync tamamlandı: {result.get('orders_fetched', 0)} sipariş ({duration:.1f}s)")
        
        return {
            "status": "success",
            "orders_fetched": result.get('orders_fetched', 0),
            "items_stored": result.get('items_stored', 0),
            "duration_seconds": round(duration, 2),
            "date_range": {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "days": days
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Trendyol sync hatası: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Trendyol sync sırasında hata oluştu: {str(e)}"
        )


@router.get("/test-connection")
async def test_trendyol_connection() -> Dict[str, Any]:
    """
    Trendyol API bağlantısını test et
    
    Returns:
        Bağlantı durumu ve temel bilgiler
    """
    try:
        settings = get_settings()
        
        # Credentials kontrolü
        if not settings.trendyol_supplier_id or not settings.trendyol_api_secret:
            return {
                "status": "error",
                "message": "Trendyol API credentials eksik",
                "has_supplier_id": bool(settings.trendyol_supplier_id),
                "has_api_secret": bool(settings.trendyol_api_secret),
                "timestamp": datetime.now().isoformat()
            }
        
        # Client oluştur
        trendyol_client = TrendyolAPIClient(
            supplier_id=settings.trendyol_supplier_id,
            api_key=settings.trendyol_api_key,
            api_secret=settings.trendyol_api_secret
        )
        
        # Test: Bugünün 1 sayfasını çek
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        result = await asyncio.to_thread(
            trendyol_client.get_shipment_packages,
            status=None,
            start_date=yesterday,
            end_date=today,
            page=0,
            size=10
        )
        
        return {
            "status": "success",
            "message": "Trendyol API bağlantısı başarılı",
            "supplier_id": settings.trendyol_supplier_id,
            "test_query": {
                "page": result.get('page', 0),
                "size": result.get('size', 0),
                "total_elements": result.get('totalElements', 0)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Trendyol bağlantı testi hatası: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Trendyol API bağlantısı başarısız: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
