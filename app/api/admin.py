"""
Admin Endpoints - Database Yönetimi
UYARI: Bu endpoint'ler production'da güvenli olmalı!
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
from datetime import datetime, timedelta

from database import SessionLocal, SalesOrder, SalesOrderItem, Product
from services.data_fetcher import DataFetcherService
from connectors.sentos_client import SentosAPIClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])

settings = get_settings()


@router.post("/reset-database")
async def reset_database(
    confirm: str = Query(..., description="'CONFIRM' yazarak onayla"),
    start_date: Optional[str] = Query(None, description="Temizlenecek başlangıç tarihi (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Temizlenecek bitiş tarihi (YYYY-MM-DD)")
):
    """
    ⚠️ TEHLIKELI: Database'i temizler!
    
    - confirm='CONFIRM' yazılmalı
    - Tarih verilirse sadece o aralık silinir
    - Tarih verilmezse TÜM veriler silinir!
    """
    if confirm != "CONFIRM":
        raise HTTPException(status_code=400, detail="Confirm parametresi 'CONFIRM' olmalı!")
    
    db = SessionLocal()
    try:
        if start_date and end_date:
            # Sadece belirli tarih aralığını sil
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            
            logger.warning(f"🗑️  Siliniyor: {start_date} - {end_date}")
            
            # Orders
            orders_to_delete = db.query(SalesOrder).filter(
                SalesOrder.order_date >= start_dt,
                SalesOrder.order_date < end_dt
            ).all()
            
            order_ids = [o.id for o in orders_to_delete]
            
            # Items
            items_deleted = db.query(SalesOrderItem).filter(
                SalesOrderItem.order_id.in_(order_ids)
            ).delete(synchronize_session=False) if order_ids else 0
            
            orders_deleted = db.query(SalesOrder).filter(
                SalesOrder.order_date >= start_dt,
                SalesOrder.order_date < end_dt
            ).delete(synchronize_session=False)
            
            db.commit()
            
            logger.info(f"✅ Silindi: {orders_deleted} sipariş, {items_deleted} item ({start_date} - {end_date})")
            
            return {
                "status": "success",
                "message": f"Tarih aralığı temizlendi: {start_date} - {end_date}",
                "orders_deleted": orders_deleted,
                "items_deleted": items_deleted
            }
        else:
            # TÜM verileri sil (products hariç!)
            logger.warning("🗑️  TÜM SİPARİŞLER SİLİNİYOR!")
            
            items_deleted = db.query(SalesOrderItem).delete()
            orders_deleted = db.query(SalesOrder).delete()
            
            db.commit()
            
            logger.info(f"✅ TÜM VERİ SİLİNDİ: {orders_deleted} sipariş, {items_deleted} item")
            
            return {
                "status": "success",
                "message": "TÜM sipariş verileri silindi (ürünler korundu)",
                "orders_deleted": orders_deleted,
                "items_deleted": items_deleted
            }
            
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Database reset hatası: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/full-resync")
async def full_resync(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    clear_first: bool = Query(False, description="Önce o tarihleri temizle")
):
    """
    Database'i temizleyip yeniden sync yapar
    
    Adımlar:
    1. (Opsiyonel) Belirtilen tarih aralığını temizle
    2. Products sync (batch)
    3. Orders sync
    """
    try:
        logger.info(f"🔄 FULL RESYNC başlatılıyor: {start_date} - {end_date}")
        
        db = SessionLocal()
        
        # 1. Temizle (istenirse)
        if clear_first:
            logger.info("🗑️  Mevcut veriler temizleniyor...")
            
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            
            orders_to_delete = db.query(SalesOrder).filter(
                SalesOrder.order_date >= start_dt,
                SalesOrder.order_date < end_dt
            ).all()
            
            order_ids = [o.id for o in orders_to_delete]
            
            items_deleted = db.query(SalesOrderItem).filter(
                SalesOrderItem.order_id.in_(order_ids)
            ).delete(synchronize_session=False) if order_ids else 0
            
            orders_deleted = db.query(SalesOrder).filter(
                SalesOrder.order_date >= start_dt,
                SalesOrder.order_date < end_dt
            ).delete(synchronize_session=False)
            
            db.commit()
            logger.info(f"✅ Temizlendi: {orders_deleted} sipariş, {items_deleted} item")
        
        db.close()
        
        # 2. Sentos client
        sentos = SentosAPIClient(
            api_url=settings.sentos_api_url,
            api_key=settings.sentos_api_key,
            api_secret=settings.sentos_api_secret
        )
        
        fetcher = DataFetcherService(sentos_client=sentos)
        
        # 3. ÖNCE PRODUCTS SYNC (rate limit için önemli!)
        # ⚠️ KÜÇÜK BATCH - Render timeout önlemek için
        logger.info("📦 Products sync başlatılıyor...")
        db = SessionLocal()
        try:
            # Max 20 sayfa = 2000 ürün (timeout önlemek için)
            product_count = fetcher.sync_products_from_sentos(db, max_pages=20)
            logger.info(f"✅ Products sync tamamlandı: {product_count} ürün")
        finally:
            db.close()
        
        # 4. ORDERS SYNC
        logger.info(f"📊 Orders sync başlatılıyor: {start_date} - {end_date}")
        result = fetcher.fetch_and_store_orders(
            start_date=start_date,
            end_date=end_date,
            marketplace=None,
            clear_existing=False
        )
        
        logger.info(f"✅ FULL RESYNC tamamlandı!")
        
        return {
            "status": "success",
            "message": "Full resync tamamlandı",
            "products_synced": product_count,
            "orders_synced": result.get("orders_fetched", 0),
            "items_synced": result.get("items_stored", 0),
            "duration_seconds": result.get("duration_seconds", 0)
        }
        
    except Exception as e:
        logger.error(f"❌ Full resync hatası: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database-stats")
async def database_stats():
    """
    Database istatistikleri
    """
    db = SessionLocal()
    try:
        # Counts
        total_products = db.query(Product).count()
        total_orders = db.query(SalesOrder).count()
        total_items = db.query(SalesOrderItem).count()
        
        # Tarih aralığı
        from sqlalchemy import func
        date_range = db.query(
            func.min(SalesOrder.order_date).label('min_date'),
            func.max(SalesOrder.order_date).label('max_date')
        ).first()
        
        # Status dağılımı
        from collections import defaultdict
        status_dist = defaultdict(int)
        orders = db.query(SalesOrder).all()
        for o in orders:
            status_dist[o.order_status] += 1
        
        return {
            "products": total_products,
            "orders": total_orders,
            "items": total_items,
            "date_range": {
                "min": date_range.min_date.strftime("%Y-%m-%d") if date_range.min_date else None,
                "max": date_range.max_date.strftime("%Y-%m-%d") if date_range.max_date else None
            },
            "status_distribution": dict(status_dist)
        }
        
    finally:
        db.close()
