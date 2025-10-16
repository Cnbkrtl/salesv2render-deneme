"""
Data Management Endpoints
Veri çekme ve ürün sync işlemleri
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models import FetchDataRequest, FetchDataResponse
from app.core.config import get_settings
from connectors.sentos_client import SentosAPIClient
from services.data_fetcher import DataFetcherService
from database.connection import SessionLocal

router = APIRouter(prefix="/api/data", tags=["Data Management"])


def get_data_fetcher() -> DataFetcherService:
    """DataFetcherService dependency"""
    settings = get_settings()
    sentos = SentosAPIClient(
        api_url=settings.sentos_api_url,
        api_key=settings.sentos_api_key,
        api_secret=settings.sentos_api_secret
    )
    return DataFetcherService(sentos)


@router.post("/fetch", response_model=FetchDataResponse)
async def fetch_sales_data(
    request: FetchDataRequest,
    fetcher: DataFetcherService = Depends(get_data_fetcher)
):
    """
    Sentos API'den satış verilerini çeker ve database'e kaydeder
    
    **Özellikler:**
    - Retail otomatik filtrelenir (sadece ECOMMERCE)
    - Status 5, 6, 99 çekilir
    - item_status="rejected" ile gerçek iadeler tespit edilir
    - Kargo ücretleri kaydedilir
    - Ürün maliyetleri (product cache'den)
    """
    try:
        start_time = datetime.now()
        
        result = fetcher.fetch_and_store_orders(
            start_date=request.start_date,
            end_date=request.end_date,
            marketplace=request.marketplace,
            clear_existing=request.clear_existing
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', 'Unknown error'))
        
        duration = result.get('duration_seconds', 0)
        
        return FetchDataResponse(
            success=True,
            records_fetched=result['orders_fetched'],
            records_stored=result['items_stored'],
            message=f"Successfully fetched and stored {result['items_stored']} items from {result['orders_fetched']} orders",
            duration_seconds=duration
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-products")
async def sync_products(
    background_tasks: BackgroundTasks,
    max_pages: int = 10,
    fetcher: DataFetcherService = Depends(get_data_fetcher)
):
    """
    Sentos'tan ürünleri çeker ve maliyet bilgilerini günceller (background task)
    
    **Önemli:**
    - İşlem arka planda çalışır, hemen response döner
    - purchase_price: KDV'siz alış fiyatı
    - vat_rate: KDV oranı (varsayılan %10)
    - purchase_price_with_vat: KDV'li maliyet (hesaplanır)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔄 sync_products endpoint çağrıldı - max_pages: {max_pages}")
    
    def run_sync():
        try:
            db = SessionLocal()
            logger.info("📊 Database bağlantısı oluşturuldu")
            
            logger.info("🚀 sync_products_from_sentos başlatılıyor...")
            total_synced = fetcher.sync_products_from_sentos(db, max_pages=max_pages)
            
            logger.info(f"✅ Senkronizasyon tamamlandı: {total_synced} ürün")
            db.close()
        except Exception as e:
            logger.error(f"❌ Senkronizasyon hatası: {str(e)}")
            logger.exception(e)
    
    # Background task olarak çalıştır
    background_tasks.add_task(run_sync)
    
    return {
        "success": True,
        "message": f"Product sync başlatıldı (max {max_pages} pages). İşlem arka planda devam ediyor.",
        "status": "running"
    }
