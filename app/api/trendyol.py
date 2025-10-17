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
    days: int = Query(default=14, ge=1, le=90, description="Son kaç günün verisi çekilecek (1-90 arası)")
) -> Dict[str, Any]:
    """
    Manuel Trendyol sipariş senkronizasyonu
    
    Args:
        days: Son kaç günün verisi çekilecek (varsayılan: 14, maksimum: 90)
    
    Returns:
        Sync sonuçları (sipariş sayısı, item sayısı, süre)
    """
    try:
        settings = get_settings()
        
        # Trendyol credentials kontrolü - 3 bilgi de gerekli
        if not settings.trendyol_supplier_id or not settings.trendyol_api_key or not settings.trendyol_api_secret:
            missing = []
            if not settings.trendyol_supplier_id:
                missing.append("TRENDYOL_SUPPLIER_ID")
            if not settings.trendyol_api_key:
                missing.append("TRENDYOL_API_KEY")
            if not settings.trendyol_api_secret:
                missing.append("TRENDYOL_API_SECRET")
            
            raise HTTPException(
                status_code=400,
                detail=f"Trendyol API credentials eksik: {', '.join(missing)}"
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
        
        # Credentials kontrolü - 3 bilgi de gerekli
        if not settings.trendyol_supplier_id or not settings.trendyol_api_key or not settings.trendyol_api_secret:
            missing = []
            if not settings.trendyol_supplier_id:
                missing.append("TRENDYOL_SUPPLIER_ID")
            if not settings.trendyol_api_key:
                missing.append("TRENDYOL_API_KEY")
            if not settings.trendyol_api_secret:
                missing.append("TRENDYOL_API_SECRET")
                
            return {
                "status": "error",
                "message": f"Trendyol API credentials eksik: {', '.join(missing)}",
                "has_supplier_id": bool(settings.trendyol_supplier_id),
                "has_api_key": bool(settings.trendyol_api_key),
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


@router.get("/product-stats")
async def get_trendyol_product_stats(
    days: int = Query(default=7, ge=1, le=90, description="Son kaç günün verisi (1-90 arası)"),
    limit: int = Query(default=20, ge=1, le=100, description="Kaç ürün gösterilecek (top N)"),
    sort_by: str = Query(default="total_revenue", description="Sıralama kriteri"),
    include_sentos: bool = Query(default=True, description="Sentos verisiyle birleştir mi?")
) -> Dict[str, Any]:
    """
    Trendyol ürün performans istatistikleri
    
    **Özellikler:**
    - Trendyol API'den direkt ürün istatistikleri
    - Sentos verisiyle birleştirme (opsiyonel)
    - Top N ürün listesi (sat ılan, ciro, kar, vs.)
    - Marketplace bazında dağılım
    
    **Metrikler:**
    - order_count: Sipariş sayısı
    - sold_quantity: Satılan adet
    - revenue: Ciro
    - favorite_count: Favoriye eklenme
    - visit_count: Görüntülenme
    - profit: Kar (ciro - maliyet)
    - profit_margin: Kar marjı (%)
    
    Args:
        days: Son kaç günün verisi (1-90)
        limit: Top N ürün (1-100)
        sort_by: Sıralama (total_revenue, profit, total_sold_quantity, etc.)
        include_sentos: Sentos verisiyle birleştir
    
    Returns:
        {
            "top_products": [...],
            "marketplace_breakdown": {...},
            "summary": {...},
            "date_range": {...}
        }
    """
    try:
        settings = get_settings()
        
        # Trendyol credentials kontrolü
        if not settings.trendyol_supplier_id or not settings.trendyol_api_key or not settings.trendyol_api_secret:
            raise HTTPException(
                status_code=400,
                detail="Trendyol API credentials eksik"
            )
        
        start_time = datetime.now()
        logger.info(f"📊 Trendyol product stats başlatıldı (son {days} gün)")
        
        # Tarih aralığı
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Trendyol client ve analytics service
        from connectors.trendyol_client import TrendyolAPIClient
        from services.trendyol_product_analytics import TrendyolProductAnalyticsService
        from database import SessionLocal
        
        trendyol_client = TrendyolAPIClient(
            supplier_id=settings.trendyol_supplier_id,
            api_key=settings.trendyol_api_key,
            api_secret=settings.trendyol_api_secret
        )
        
        analytics_service = TrendyolProductAnalyticsService(trendyol_client=trendyol_client)
        
        # Trendyol stats çek
        trendyol_stats = await asyncio.to_thread(
            analytics_service.fetch_trendyol_product_stats,
            start_date=start_date,
            end_date=end_date,
            max_pages=10  # Max 500 ürün (10 * 50)
        )
        
        # Sentos verisiyle birleştir (opsiyonel)
        combined_data = []
        if include_sentos:
            # TODO: Sentos ürün performans verisini çek
            # Şimdilik boş liste
            sentos_product_data = []
            
            db = SessionLocal()
            try:
                combined_data = analytics_service.combine_with_sentos_data(
                    db=db,
                    trendyol_stats=trendyol_stats,
                    sentos_product_data=sentos_product_data
                )
            finally:
                db.close()
        else:
            # Sadece Trendyol verisi
            combined_data = [
                {
                    'marketplace': 'Trendyol',
                    'barcode': stat.get('barcode'),
                    'product_code': stat.get('productCode'),
                    'product_name': stat.get('productName'),
                    'brand': stat.get('brand'),
                    'category': stat.get('categoryName'),
                    'price': stat.get('price', 0),
                    'discounted_price': stat.get('discountedPrice', 0),
                    'stock': stat.get('stock', 0),
                    'order_count': stat.get('orderCount', 0),
                    'sold_quantity': stat.get('soldQuantity', 0),
                    'revenue': stat.get('revenue', 0),
                    'favorite_count': stat.get('favoriteCount', 0),
                    'visit_count': stat.get('visitCount', 0),
                    'total_order_count': stat.get('orderCount', 0),
                    'total_revenue': stat.get('revenue', 0),
                    'total_sold_quantity': stat.get('soldQuantity', 0),
                    'source': 'trendyol_api'
                }
                for stat in trendyol_stats
            ]
        
        # Top N ürünleri al
        top_products = analytics_service.get_top_products(
            combined_data=combined_data,
            sort_by=sort_by,
            limit=limit
        )
        
        # Marketplace breakdown
        marketplace_breakdown = analytics_service.get_marketplace_breakdown(
            combined_data=combined_data
        )
        
        # Summary
        total_revenue = sum(p.get('total_revenue', 0) for p in combined_data)
        total_sold = sum(p.get('total_sold_quantity', 0) for p in combined_data)
        total_orders = sum(p.get('total_order_count', 0) for p in combined_data)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ Trendyol product stats tamamlandı ({duration:.1f}s)")
        
        return {
            "status": "success",
            "top_products": top_products,
            "marketplace_breakdown": marketplace_breakdown,
            "summary": {
                "total_products": len(combined_data),
                "total_revenue": total_revenue,
                "total_sold_quantity": total_sold,
                "total_order_count": total_orders,
                "avg_revenue_per_product": total_revenue / len(combined_data) if combined_data else 0
            },
            "date_range": {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "days": days
            },
            "filters": {
                "sort_by": sort_by,
                "limit": limit,
                "include_sentos": include_sentos
            },
            "duration_seconds": round(duration, 2),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Trendyol product stats hatası: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Trendyol product stats sırasında hata oluştu: {str(e)}"
        )
