"""
Admin Endpoints - Database Yönetimi
UYARI: Bu endpoint'ler production'da güvenli olmalı!
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional
import logging
import asyncio
from datetime import datetime, timedelta

from database import SessionLocal, SalesOrder, SalesOrderItem, Product
from services.data_fetcher import DataFetcherService
from connectors.sentos_client import SentosAPIClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])

settings = get_settings()

# 🆕 Global status tracker
resync_status = {
    "running": False,
    "progress": "",
    "start_time": None,
    "error": None
}


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
    background_tasks: BackgroundTasks,
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    clear_first: bool = Query(False, description="Önce o tarihleri temizle")
):
    """
    Database'i temizleyip yeniden sync yapar (BACKGROUND TASK)
    
    ⚠️ ÖNEMLİ: 
    - İşlem background'da çalışır, health check'i bloklamaz
    - Scheduler otomatik durdurulur ve sonra devam ettirilir
    - Status: /api/admin/resync-status endpoint'inden takip edilir
    
    Adımlar:
    1. Scheduler PAUSE
    2. (Opsiyonel) Belirtilen tarih aralığını temizle
    3. Products sync (batch)
    4. Orders sync
    5. Scheduler RESUME
    """
    # Status kontrolü
    if resync_status["running"]:
        raise HTTPException(
            status_code=409, 
            detail="Resync zaten çalışıyor! Status endpoint'ini kontrol edin."
        )
    
    # Background task başlat
    background_tasks.add_task(
        _run_full_resync_task,
        start_date=start_date,
        end_date=end_date,
        clear_first=clear_first
    )
    
    # Hemen cevap dön (non-blocking)
    return {
        "status": "started",
        "message": "Full resync background'da başlatıldı",
        "start_date": start_date,
        "end_date": end_date,
        "check_status": "/api/admin/resync-status"
    }


async def _run_full_resync_task(start_date: str, end_date: str, clear_first: bool):
    """Background task: Full resync işlemini çalıştırır"""
    resync_status["running"] = True
    resync_status["start_time"] = datetime.now()
    resync_status["error"] = None
    resync_status["progress"] = "Başlatılıyor..."
    
    try:
        logger.info(f"🔄 FULL RESYNC başlatılıyor: {start_date} - {end_date}")
        resync_status["progress"] = "Scheduler duraklatılıyor..."
        
        # 1. SCHEDULER'I DURDUR!
        from services.scheduled_sync import get_scheduler
        scheduler = get_scheduler()
        scheduler.pause()
        logger.warning("⏸️  SCHEDULER PAUSED - Full resync in progress")
        
        try:
            # 2. Temizle (istenirse)
            if clear_first:
                resync_status["progress"] = "Database temizleniyor..."
                logger.info("🗑️  Mevcut veriler temizleniyor...")
                
                # Async olarak çalıştır (thread pool'da)
                await asyncio.to_thread(_clear_database, start_date, end_date)
            
            # 3. Products sync (async)
            resync_status["progress"] = "Products sync yapılıyor..."
            logger.info("📦 Products sync başlatılıyor...")
            
            product_count = await asyncio.to_thread(_sync_products)
            logger.info(f"✅ Products sync tamamlandı: {product_count} ürün")
            
            # 4. Orders sync (async)
            resync_status["progress"] = "Orders sync yapılıyor..."
            logger.info(f"📊 Orders sync başlatılıyor: {start_date} - {end_date}")
            
            result = await asyncio.to_thread(
                _sync_orders, 
                start_date, 
                end_date
            )
            
            logger.info(f"✅ FULL RESYNC tamamlandı!")
            resync_status["progress"] = "Tamamlandı! ✅"
            resync_status["result"] = {
                "products_synced": product_count,
                "orders_synced": result.get("orders_fetched", 0),
                "items_synced": result.get("items_stored", 0),
                "duration_seconds": result.get("duration_seconds", 0)
            }
        
        finally:
            # 5. SCHEDULER'I YENİDEN BAŞLAT!
            scheduler.resume()
            logger.info("▶️  SCHEDULER RESUMED - Full resync completed")
    
    except Exception as e:
        # HATA DURUMUNDA DA SCHEDULER'I BAŞLAT!
        try:
            from services.scheduled_sync import get_scheduler
            scheduler = get_scheduler()
            scheduler.resume()
            logger.warning("▶️  SCHEDULER RESUMED after error")
        except:
            pass
        
        logger.error(f"❌ Full resync hatası: {e}", exc_info=True)
        resync_status["progress"] = f"HATA: {str(e)}"
        resync_status["error"] = str(e)
    
    finally:
        resync_status["running"] = False


def _clear_database(start_date: str, end_date: str):
    """Sync helper: Database temizle"""
    db = SessionLocal()
    try:
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
    finally:
        db.close()


def _sync_products():
    """Sync helper: Products sync"""
    sentos = SentosAPIClient(
        api_url=settings.sentos_api_url,
        api_key=settings.sentos_api_key,
        api_secret=settings.sentos_api_secret
    )
    fetcher = DataFetcherService(sentos_client=sentos)
    
    db = SessionLocal()
    try:
        # ⚠️ ÇOK KÜÇÜK BATCH: 10 sayfa = 1000 ürün
        # Her 5 sayfada sleep (health check için)
        return fetcher.sync_products_from_sentos(db, max_pages=10)
    finally:
        db.close()


def _sync_orders(start_date: str, end_date: str):
    """Sync helper: Orders sync"""
    sentos = SentosAPIClient(
        api_url=settings.sentos_api_url,
        api_key=settings.sentos_api_key,
        api_secret=settings.sentos_api_secret
    )
    fetcher = DataFetcherService(sentos_client=sentos)
    
    return fetcher.fetch_and_store_orders(
        start_date=start_date,
        end_date=end_date,
        marketplace=None,
        clear_existing=False
    )


@router.get("/resync-status")
async def get_resync_status():
    """Full resync durumunu kontrol et"""
    return {
        "running": resync_status["running"],
        "progress": resync_status["progress"],
        "start_time": resync_status["start_time"].isoformat() if resync_status["start_time"] else None,
        "error": resync_status["error"],
        "result": resync_status.get("result")
    }


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


@router.get("/check-date/{date}")
async def check_date_data(date: str):
    """
    Belirli bir tarihteki veriyi detaylı kontrol et
    Format: YYYY-MM-DD
    """
    db = SessionLocal()
    try:
        from datetime import datetime, timedelta
        from collections import Counter
        
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD: {e}")
        
        next_date = target_date + timedelta(days=1)
        
        # Siparişler
        orders = db.query(SalesOrder).filter(
            SalesOrder.order_date >= target_date,
            SalesOrder.order_date < next_date
        ).all()
        
        if not orders:
            return {
                "date": date,
                "message": "No data found for this date",
                "summary": {
                    "total_orders": 0,
                    "total_items": 0
                }
            }
        
        # Status dağılımı
        status_count = Counter([o.order_status for o in orders])
        
        # Items
        order_ids = [o.id for o in orders]
        items = db.query(SalesOrderItem).filter(
            SalesOrderItem.order_id.in_(order_ids)
        ).all() if order_ids else []
        
        # İptal/İade
        iptal_orders = [o for o in orders if o.order_status == 6]
        iptal_order_ids = [o.id for o in iptal_orders]
        iptal_items = [i for i in items if i.order_id in iptal_order_ids]
        
        # Net
        net_orders = [o for o in orders if o.order_status != 6]
        net_order_ids = [o.id for o in net_orders]
        net_items = [i for i in items if i.order_id in net_order_ids]
        
        # Ciro hesaplama (safe)
        try:
            net_urun_ciro = sum(
                (i.unit_price or 0) * (i.quantity or 0) 
                for i in net_items
            )
            net_kargo = sum(
                o.shipping_total or 0 
                for o in net_orders
            )
            net_ciro = net_urun_ciro + net_kargo
            
            iptal_urun = sum(
                (i.unit_price or 0) * (i.quantity or 0) 
                for i in iptal_items
            )
            iptal_kargo = sum(
                o.shipping_total or 0 
                for o in iptal_orders
            )
            iptal_total = iptal_urun + iptal_kargo
            
            brut_ciro = net_ciro + iptal_total
        except Exception as calc_error:
            return {
                "date": date,
                "error": f"Calculation error: {str(calc_error)}",
                "summary": {
                    "total_orders": len(orders),
                    "total_items": len(items)
                }
            }
        
        return {
            "date": date,
            "summary": {
                "total_orders": len(orders),
                "total_items": len(items),
                "iptal_orders": len(iptal_orders),
                "net_orders": len(net_orders),
                "net_items": len(net_items)
            },
            "status_distribution": dict(status_count),
            "revenue": {
                "net_urun_ciro": round(net_urun_ciro, 2),
                "net_kargo": round(net_kargo, 2),
                "net_ciro": round(net_ciro, 2),
                "iptal_urun": round(iptal_urun, 2),
                "iptal_kargo": round(iptal_kargo, 2),
                "iptal_total": round(iptal_total, 2),
                "brut_ciro": round(brut_ciro, 2)
            },
            "comparison": {
                "expected_net_ciro": 144412.84,
                "actual_net_ciro": round(net_ciro, 2),
                "difference": round(net_ciro - 144412.84, 2),
                "difference_percent": round((net_ciro - 144412.84) / 144412.84 * 100, 2) if net_ciro > 0 else 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Check date error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        db.close()
