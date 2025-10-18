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
    
    scheduler = None
    
    try:
        logger.info(f"🔄 FULL RESYNC başlatılıyor: {start_date} - {end_date}")
        resync_status["progress"] = "Scheduler duraklatılıyor..."
        
        # 1. SCHEDULER'I DURDUR!
        from services.scheduled_sync import get_scheduler
        scheduler = get_scheduler()
        scheduler.pause()
        logger.warning("⏸️  SCHEDULER PAUSED - Full resync in progress")
        
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
    
    except Exception as e:
        logger.error(f"❌ Full resync hatası: {e}", exc_info=True)
        resync_status["progress"] = f"HATA: {str(e)}"
        resync_status["error"] = str(e)
    
    finally:
        # 🆕 HER DURUMDA SCHEDULER'I YENİDEN BAŞLAT!
        resync_status["running"] = False
        
        if scheduler:
            try:
                scheduler.resume()
                logger.info("▶️  SCHEDULER RESUMED - Full resync completed")
            except Exception as resume_error:
                logger.error(f"❌ Scheduler resume hatası: {resume_error}")
        else:
            # Scheduler alınamadıysa tekrar dene
            try:
                from services.scheduled_sync import get_scheduler
                scheduler = get_scheduler()
                scheduler.resume()
                logger.warning("▶️  SCHEDULER RESUMED (fallback)")
            except Exception as fallback_error:
                logger.error(f"❌ Scheduler resume fallback hatası: {fallback_error}")


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
    """Sync helper: Orders sync (Sentos + Trendyol)"""
    from connectors.trendyol_client import TrendyolAPIClient
    from services.trendyol_data_fetcher import TrendyolDataFetcher
    
    # 1. SENTOS SYNC
    sentos = SentosAPIClient(
        api_url=settings.sentos_api_url,
        api_key=settings.sentos_api_key,
        api_secret=settings.sentos_api_secret
    )
    fetcher = DataFetcherService(sentos_client=sentos)
    
    sentos_result = fetcher.fetch_and_store_orders(
        start_date=start_date,
        end_date=end_date,
        marketplace=None,
        clear_existing=False
    )
    
    # 2. TRENDYOL SYNC
    trendyol = TrendyolAPIClient(
        api_url=settings.trendyol_api_url,
        supplier_id=settings.trendyol_supplier_id,
        api_key=settings.trendyol_api_key,
        api_secret=settings.trendyol_api_secret
    )
    trendyol_fetcher = TrendyolDataFetcher(trendyol_client=trendyol)
    
    trendyol_result = trendyol_fetcher.fetch_and_store_trendyol_orders(
        start_date=start_date,
        end_date=end_date,
        clear_existing=False
    )
    
    # Birleştir
    return {
        'sentos': sentos_result,
        'trendyol': trendyol_result,
        'total_orders': sentos_result.get('orders_count', 0) + trendyol_result.get('orders_fetched', 0)
    }


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


@router.post("/migrate-database")
async def migrate_database():
    """
    🔧 Database migration: Add missing columns
    Production database için eksik kolonları ekler
    """
    from sqlalchemy import text
    db = SessionLocal()
    try:
        results = []
        
        # Check and add 'images' column to products
        try:
            # Try to check if column exists (PostgreSQL)
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='products' AND column_name='images'
            """))
            
            if result.fetchone():
                results.append({"column": "products.images", "status": "exists", "message": "Column already exists"})
            else:
                # Add column
                db.execute(text("""
                    ALTER TABLE products 
                    ADD COLUMN images TEXT DEFAULT '[]'
                """))
                db.commit()
                results.append({"column": "products.images", "status": "added", "message": "Column added successfully"})
        except Exception as e:
            error_msg = str(e).lower()
            if 'already exists' in error_msg or 'duplicate column' in error_msg:
                results.append({"column": "products.images", "status": "exists", "message": "Column already exists"})
            else:
                results.append({"column": "products.images", "status": "error", "message": str(e)})
        
        return {
            "success": True,
            "migrations": results
        }
        
    except Exception as e:
        logger.error(f"❌ Migration error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


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


@router.get("/debug/trendyol-today")
async def debug_trendyol_today(
    date: Optional[str] = Query(None, description="Tarih (YYYY-MM-DD), default: bugün")
):
    """
    🔍 Trendyol bugünkü siparişlerini SADECE Trendyol API'den çeker ve karşılaştırır
    """
    from connectors.trendyol_client import TrendyolAPIClient
    from datetime import datetime as dt
    try:
        # Tarih belirleme
        if date:
            check_date = dt.strptime(date, "%Y-%m-%d").date()
        else:
            check_date = dt.now().date()
        
        logger.info(f"🔍 Checking Trendyol orders for: {check_date}")
        
        # Trendyol client
        trendyol = TrendyolAPIClient(
            api_url=settings.trendyol_api_url,
            supplier_id=settings.trendyol_supplier_id,
            api_key=settings.trendyol_api_key,
            api_secret=settings.trendyol_api_secret
        )
        
        # Bugünün siparişlerini çek (start_date = end_date = bugün)
        start_str = check_date.strftime("%Y-%m-%d")
        end_str = (check_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        logger.info(f"📡 Fetching from Trendyol API: {start_str} to {end_str}")
        
        packages = trendyol.get_orders_by_date_range(
            start_date=dt.strptime(start_str, "%Y-%m-%d"),
            end_date=dt.strptime(end_str, "%Y-%m-%d")
        )
        
        logger.info(f"📦 Fetched {len(packages)} Trendyol packages from API")
        
        # DEBUG: İlk paketi loga yaz
        if packages:
            import json
            logger.info("🔍 First Trendyol API package: %s", json.dumps(packages[0], ensure_ascii=False, indent=2))
        
        # 🎯 CRITICAL FIX: Trendyol API orderDate'i GMT+3 timezone'unda veriyor
        # Sistem timestamp'i naive (local timezone) olarak hesaplıyor
        # GMT+3'e çevirmek için 3 SAAT EKLEMELIYIZ
        from datetime import datetime as dt_calc
        
        # Local naive timestamp hesapla
        check_date_naive_start = dt_calc.combine(check_date, dt_calc.min.time())
        check_date_naive_end = dt_calc.combine(check_date + timedelta(days=1), dt_calc.min.time())
        
        # GMT+3 timezone için 3 saat (10800 saniye) EKLE
        # Örnek: 18 Ekim 00:00 naive = 1760734800000
        #        18 Ekim 00:00 GMT+3 = 1760745600000 (+ 10800000 ms)
        gmt3_offset_ms = 3 * 60 * 60 * 1000  # 10800000 milliseconds
        check_date_start_ts = int(check_date_naive_start.timestamp() * 1000) + gmt3_offset_ms
        check_date_end_ts = int(check_date_naive_end.timestamp() * 1000) + gmt3_offset_ms
        
        logger.info(f"🔍 Filtering by orderDate: {check_date_start_ts} to {check_date_end_ts}")
        
        filtered_packages = []
        for pkg in packages:
            order_date_ts = pkg.get('orderDate', 0)
            if check_date_start_ts <= order_date_ts < check_date_end_ts:
                filtered_packages.append(pkg)
        
        logger.info(f"✅ Filtered to {len(filtered_packages)} packages (was {len(packages)}) by orderDate")
        
        # 🔄 Paketleri orderNumber'a göre grupla
        from collections import defaultdict
        orders_map = defaultdict(list)
        for pkg in filtered_packages:
            order_number = pkg.get('orderNumber')
            if order_number:
                orders_map[order_number].append(pkg)
        
        logger.info(f"📊 Grouped into {len(orders_map)} unique orders from {len(filtered_packages)} packages")
        
        # DEBUG: Shipped siparişlerinin orderDate'lerini kontrol et
        shipped_orders_debug = []
        for pkg in filtered_packages:
            if pkg.get('status') == 'Shipped':
                order_date_ts = pkg.get('orderDate', 0)
                order_date_readable = dt.fromtimestamp(order_date_ts / 1000).strftime('%Y-%m-%d %H:%M:%S') if order_date_ts else 'N/A'
                shipped_orders_debug.append({
                    'orderNumber': pkg.get('orderNumber'),
                    'orderDate': order_date_readable,
                    'orderDate_ts': order_date_ts
                })
        if shipped_orders_debug:
            import json
            logger.info(f"🚢 Shipped orders (count: {len(shipped_orders_debug)}): {json.dumps(shipped_orders_debug[:5], ensure_ascii=False, indent=2)}")
        
        # Analiz - Sipariş bazında
        # NET = Brüt - İptal/İade
        total_quantity = 0  # NET adet
        total_amount = 0.0  # NET ciro
        
        iptal_quantity = 0  # İptal/İade adet
        iptal_amount = 0.0  # İptal/İade ciro
        
        brut_quantity = 0  # Brüt adet (tümü)
        brut_amount = 0.0  # Brüt ciro (tümü)
        
        status_counts = {}
        iptal_count = 0
        aktif_count = 0
        
        order_details = []
        
        for order_number, pkgs in orders_map.items():
            # Bir siparişin birden fazla paketi olabilir
            # İlk paketin statusunu al (hepsi aynı olmalı)
            first_pkg = pkgs[0]
            status = first_pkg.get('status')
            
            # Status sayımı
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1
            
            # İptal mi?
            is_cancelled = status in ["Cancelled", "UnSupplied", "Returned"]
            
            if is_cancelled:
                iptal_count += 1
            else:
                aktif_count += 1
            
            # Tüm paketlerdeki items'ları topla
            order_total_qty = 0
            order_total_amount = 0.0
            order_items_count = 0
            
            for package in pkgs:
                # Items - Trendyol'da 'lines' veya 'orderLines' olabilir
                items = package.get('lines', package.get('orderLines', []))
                order_items_count += len(items)
                
                for item in items:
                    qty = item.get('quantity', 0)
                    price = item.get('price', 0) or item.get('unitPrice', 0)
                    
                    order_total_qty += qty
                    order_total_amount += (qty * price)
            
            # Brüt toplam (hepsi)
            brut_quantity += order_total_qty
            brut_amount += order_total_amount
            
            # İptal/İade ayrı topla
            if is_cancelled:
                iptal_quantity += order_total_qty
                iptal_amount += order_total_amount
            else:
                # NET toplama ekle (iptal değilse)
                total_quantity += order_total_qty
                total_amount += order_total_amount
            
            order_details.append({
                "order_number": order_number,
                "status": status,
                "is_cancelled": is_cancelled,
                "package_count": len(pkgs),
                "items_count": order_items_count,
                "total_quantity": order_total_qty,
                "total_amount": round(order_total_amount, 2)
            })
        
        # Database'den kontrol
        db = SessionLocal()
        try:
            db_orders = db.query(SalesOrder).filter(
                SalesOrder.marketplace == "Trendyol",
                SalesOrder.order_date >= dt.combine(check_date, dt.min.time()),
                SalesOrder.order_date < dt.combine(check_date + timedelta(days=1), dt.min.time())
            ).all()
            
            db_net_orders = [o for o in db_orders if o.order_status not in [6, 99]]
            db_iptal_orders = [o for o in db_orders if o.order_status in [6, 99]]
            
            db_items = []
            for order in db_net_orders:
                items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order.id).all()
                db_items.extend(items)
            
            db_total_qty = sum(item.quantity for item in db_items)
            db_total_amount = sum((item.quantity * item.unit_price) for item in db_items)
            
        finally:
            db.close()
        
        # Karşılaştırma
        return {
            "date": str(check_date),
            "api_data": {
                "total_packages_raw": len(packages),
                "total_packages_today": len(filtered_packages),
                "unique_order_numbers": len(orders_map),
                
                # Brüt (Tüm siparişler)
                "brut_orders": len(orders_map),
                "brut_quantity": brut_quantity,
                "brut_amount": round(brut_amount, 2),
                
                # İptal/İade
                "iptal_iade_orders": iptal_count,
                "iptal_iade_quantity": iptal_quantity,
                "iptal_iade_amount": round(iptal_amount, 2),
                
                # NET = Brüt - İptal/İade
                "net_orders": aktif_count,
                "net_quantity": total_quantity,
                "net_amount": round(total_amount, 2),
                
                # Eski alan isimleri (geriye dönük uyumluluk)
                "aktif_orders": aktif_count,
                "iptal_orders": iptal_count
            },
            "database_data": {
                "total_orders": len(db_orders),
                "aktif_orders": len(db_net_orders),
                "iptal_orders": len(db_iptal_orders),
                "total_items": len(db_items),
                "total_quantity": db_total_qty,
                "total_amount": round(db_total_amount, 2)
            },
            "status_distribution": status_counts,
            "comparison": {
                "orders_match": len(orders_map) == len(db_orders),
                "quantity_match": total_quantity == db_total_qty,
                "amount_match": round(total_amount, 2) == round(db_total_amount, 2),
                "orders_diff": len(orders_map) - len(db_orders),
                "quantity_diff": total_quantity - db_total_qty,
                "amount_diff": round(total_amount - db_total_amount, 2)
            },
            "all_orders": order_details,  # TÜM siparişler
            "order_samples": order_details[:10]  # İlk 10 sipariş örneği (eski)
        }
        
    except Exception as e:
        logger.error(f"❌ Trendyol debug error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/debug/sentos-today")
async def debug_sentos_today(
    date: Optional[str] = Query(None, description="Tarih (YYYY-MM-DD), default: bugün")
):
    """
    🔍 Sentos'tan bugünkü siparişleri çeker (Trendyol HARİÇ - diğer marketplace'ler)
    """
    from connectors.sentos_client import SentosAPIClient
    from datetime import datetime as dt, timedelta
    try:
        # Tarih belirleme
        if date:
            check_date = dt.strptime(date, "%Y-%m-%d").date()
        else:
            check_date = dt.now().date()
        
        logger.info(f"🔍 Checking Sentos orders (excluding Trendyol) for: {check_date}")
        
        # Sentos client
        sentos = SentosAPIClient(
            api_url=settings.sentos_api_url,
            api_key=settings.sentos_api_key,
            api_secret=settings.sentos_api_secret,
            api_cookie=getattr(settings, 'sentos_api_cookie', None)
        )
        
        # GENİŞ ARALIK: Son 7 günü çek (iadeler için makul süre)
        # İadeleri yakalamak için geniş tarih aralığı gerekli ama 30 gün çok fazla
        api_start_date = (check_date - timedelta(days=7)).strftime("%Y-%m-%d")
        api_end_date = (check_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        logger.info(f"📡 Fetching from Sentos API: {api_start_date} to {api_end_date} (7-day range for returns)")
        
        # Sentos'tan tüm siparişleri çek
        all_orders = sentos.get_all_orders(
            start_date=api_start_date,
            end_date=api_end_date,
            max_pages=10  # 7 günlük veri için 10 sayfa yeterli
        )
        
        logger.info(f"📦 Fetched {len(all_orders)} total orders from Sentos")
        
        # DEBUG: İlk siparişi göster
        if all_orders:
            import json
            logger.info(f"🔍 First Sentos order: {json.dumps(all_orders[0], ensure_ascii=False, indent=2)}")
        
        # Trendyol'u ÇIKAR - sadece diğer marketplace'leri göster
        # Sentos'ta marketplace alanı 'source' veya 'shop' olabilir
        # DAHA SIKI FİLTRE: source, shop, shop_id kontrolü
        filtered_orders = []
        trendyol_count = 0
        for order in all_orders:
            source = (order.get('source') or '').lower()
            shop = (order.get('shop') or '').lower()
            marketplace = (order.get('marketplace') or '').lower()
            shop_id = order.get('shop_id')
            
            # Trendyol tespiti - herhangi birinde 'trendyol' varsa atla
            is_trendyol = (
                'trendyol' in source or
                'trendyol' in shop or
                'trendyol' in marketplace or
                shop_id == 2  # Trendyol shop_id genelde 2
            )
            
            if is_trendyol:
                trendyol_count += 1
            else:
                filtered_orders.append(order)
        
        logger.info(f"🚫 Filtered out {trendyol_count} Trendyol orders")
        
        # DEBUG: Kalan siparişlerde hangi marketplace'ler var?
        remaining_marketplaces = {}
        cancelled_orders_debug = []
        for order in filtered_orders:
            mp = order.get('source') or order.get('shop') or order.get('marketplace') or 'Unknown'
            status = order.get('status')
            key = f"{mp} (status:{status})"
            remaining_marketplaces[key] = remaining_marketplaces.get(key, 0) + 1
            
            # İptal/iade olanları logla - ORDER_DATE VE CREATED_AT'I GÖR
            # NOT: Status 5 = Kargoya Verilmiş (normal sipariş), Status 6 = İptal
            if status in [6]:  # Sadece 6 = İptal/İade
                import json
                cancelled_orders_debug.append({
                    'order_code': order.get('order_code'),
                    'status': status,
                    'order_date': order.get('order_date'),
                    'created_at': order.get('created_at'),
                    'source': mp
                })
        
        if cancelled_orders_debug:
            import json
            logger.warning(f"⚠️ Cancelled orders found: {json.dumps(cancelled_orders_debug, ensure_ascii=False)}")
        
        logger.info(f"📊 Remaining orders by marketplace: {remaining_marketplaces}")
        logger.info(f"✅ Filtered to {len(filtered_orders)} orders (Trendyol excluded)")
        
        # 🎯 Sentos'tan gelen siparişleri de orderDate'e göre filtrele
        # GMT+3 timezone kullan (Trendyol ile aynı mantık)
        from datetime import datetime as dt_calc
        
        check_date_naive_start = dt_calc.combine(check_date, dt_calc.min.time())
        check_date_naive_end = dt_calc.combine(check_date + timedelta(days=1), dt_calc.min.time())
        
        gmt3_offset_ms = 3 * 60 * 60 * 1000
        check_date_start_ts = int(check_date_naive_start.timestamp() * 1000) + gmt3_offset_ms
        check_date_end_ts = int(check_date_naive_end.timestamp() * 1000) + gmt3_offset_ms
        
        logger.info(f"🔍 Filtering by date range: {check_date_start_ts} to {check_date_end_ts}")
        
        # Tarih alanına göre filtrele - SADECE order_date kullan (sipariş tarihi)
        # İadeler: order_date = orijinal sipariş tarihi, o günün raporuna dahil olmalı
        date_filtered_orders = []
        for order in filtered_orders:
            # SADECE order_date kullan - created_at değil!
            # created_at = Sentos'a girilme tarihi (iade için iade tarihi)
            # order_date = Müşterinin sipariş verdiği tarih (bunu kullanmalıyız)
            order_date_str = order.get('order_date')
            if not order_date_str:
                logger.warning(f"⚠️ Order {order.get('order_code')} has no order_date, skipping")
                continue
            
            try:
                # String tarih parse et
                if 'T' in order_date_str:
                    order_dt = dt.strptime(order_date_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                else:
                    # Sadece tarih kısmını al (saat varsa)
                    date_part = order_date_str.split(' ')[0]
                    order_dt = dt.strptime(date_part, '%Y-%m-%d')
                
                order_date_ts = int(order_dt.timestamp() * 1000) + gmt3_offset_ms
                
                if check_date_start_ts <= order_date_ts < check_date_end_ts:
                    date_filtered_orders.append(order)
            except Exception as e:
                logger.warning(f"⚠️ Could not parse date '{order_date_str}': {e}")
                continue
        
        logger.info(f"✅ Date filtered to {len(date_filtered_orders)} orders (was {len(filtered_orders)})")
        
        filtered_orders = date_filtered_orders
        
        # Marketplace'lere göre grupla
        marketplace_data = {}
        
        for order in filtered_orders:
            # Sentos'ta marketplace 'source' veya 'shop' alanında olabilir
            marketplace = order.get('marketplace') or order.get('source') or order.get('shop') or 'Unknown'
            status = str(order.get('status', 'Unknown'))  # String'e çevir
            
            if marketplace not in marketplace_data:
                marketplace_data[marketplace] = {
                    'total_orders': 0,
                    'brut_orders': 0,
                    'brut_quantity': 0,
                    'brut_amount': 0.0,
                    'iptal_orders': 0,
                    'iptal_quantity': 0,
                    'iptal_amount': 0.0,
                    'net_orders': 0,
                    'net_quantity': 0,
                    'net_amount': 0.0,
                    'status_counts': {}
                }
            
            mp_data = marketplace_data[marketplace]
            
            # Status sayımı
            if status not in mp_data['status_counts']:
                mp_data['status_counts'][status] = 0
            mp_data['status_counts'][status] += 1
            
            # İptal/İade kontrolü - Sentos status codes
            # Sentos Status Kodları:
            # 1 = Onay Bekliyor, 2 = Onaylandı, 3 = Tedarik Sürecinde
            # 4 = Hazırlanıyor, 5 = Kargoya Verildi, 99 = Teslim Edildi
            # 6 = İptal Edildi ← SADECE BU İPTAL!
            # NOT: Trendyol siparişleri zaten filtrelendi, bunlar LCW/Shopify/vb.
            status_str = str(status).lower()
            is_cancelled = (
                status in [6, '6'] or  # Sadece 6 = İptal Edildi
                any(
                    keyword in status_str 
                    for keyword in ['cancelled', 'iptal', 'unsupplied', 'cancel']
                )
            )
            
            # Sipariş detayları
            # Sentos'ta items 'lines' array'inde
            items = order.get('lines', order.get('items', []))
            order_qty = 0
            order_amount = 0.0
            
            for item in items:
                qty = int(item.get('quantity', 0))
                # Price string olabilir, float'a çevir
                price_str = item.get('price', '0')
                try:
                    price = float(price_str) if isinstance(price_str, str) else float(price_str or 0)
                except (ValueError, TypeError):
                    price = 0.0
                
                order_qty += qty
                order_amount += (qty * price)
            
            # Brüt toplam
            mp_data['brut_orders'] += 1
            mp_data['brut_quantity'] += order_qty
            mp_data['brut_amount'] += order_amount
            
            if is_cancelled:
                # İptal/İade
                mp_data['iptal_orders'] += 1
                mp_data['iptal_quantity'] += order_qty
                mp_data['iptal_amount'] += order_amount
            else:
                # Net
                mp_data['net_orders'] += 1
                mp_data['net_quantity'] += order_qty
                mp_data['net_amount'] += order_amount
            
            mp_data['total_orders'] += 1
        
        # Float değerleri yuvarlama
        for mp, data in marketplace_data.items():
            data['brut_amount'] = round(data['brut_amount'], 2)
            data['iptal_amount'] = round(data['iptal_amount'], 2)
            data['net_amount'] = round(data['net_amount'], 2)
        
        # Toplam özet
        total_summary = {
            'brut_orders': sum(d['brut_orders'] for d in marketplace_data.values()),
            'brut_quantity': sum(d['brut_quantity'] for d in marketplace_data.values()),
            'brut_amount': round(sum(d['brut_amount'] for d in marketplace_data.values()), 2),
            'iptal_orders': sum(d['iptal_orders'] for d in marketplace_data.values()),
            'iptal_quantity': sum(d['iptal_quantity'] for d in marketplace_data.values()),
            'iptal_amount': round(sum(d['iptal_amount'] for d in marketplace_data.values()), 2),
            'net_orders': sum(d['net_orders'] for d in marketplace_data.values()),
            'net_quantity': sum(d['net_quantity'] for d in marketplace_data.values()),
            'net_amount': round(sum(d['net_amount'] for d in marketplace_data.values()), 2)
        }
        
        return {
            "date": str(check_date),
            "total_orders_fetched": len(all_orders),
            "orders_after_trendyol_filter": len(filtered_orders),
            "total_summary": total_summary,
            "by_marketplace": marketplace_data
        }
        
    except Exception as e:
        logger.error(f"❌ Sentos debug error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
