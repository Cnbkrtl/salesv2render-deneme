"""
Scheduled Data Sync Service
Otomatik veri senkronizasyonu için background scheduler
"""
import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Optional

from services.data_fetcher import DataFetcherService
from services.trendyol_data_fetcher import TrendyolDataFetcherService
from connectors.sentos_client import SentosAPIClient
from connectors.trendyol_client import TrendyolAPIClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class ScheduledSyncService:
    """
    Zamanlanmış veri senkronizasyon servisi
    
    - Günlük tam sync: Her gün saat 02:00'de tüm veri
    - Canlı sync: 10-15 dakikada bir sadece bugünün verisi
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.is_running = False
        self.is_paused = False  # 🆕 PAUSE FLAG
        self.full_sync_time = time(2, 0)  # Sabah 02:00
        self.live_sync_interval = 600  # 10 dakika (saniye cinsinden)
        self.last_full_sync: Optional[datetime] = None
        self.last_live_sync: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Scheduler'ı başlat"""
        if self.is_running:
            logger.warning("Scheduler zaten çalışıyor")
            return
            
        self.is_running = True
        logger.info("📅 Scheduled sync service başlatıldı")
        logger.info(f"   - Günlük tam sync: Her gün {self.full_sync_time.strftime('%H:%M')}")
        logger.info(f"   - Canlı sync: Her {self.live_sync_interval//60} dakikada bir")
        
        # Background task başlat
        self._task = asyncio.create_task(self._run_scheduler())
        
    async def stop(self):
        """Scheduler'ı durdur"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduled sync service durduruldu")
    
    def pause(self):
        """🆕 Scheduler'ı duraklat (admin full resync için)"""
        self.is_paused = True
        logger.warning("⏸️  SCHEDULER PAUSED (Admin operation in progress)")
    
    def resume(self):
        """🆕 Scheduler'ı devam ettir"""
        self.is_paused = False
        logger.info("▶️  SCHEDULER RESUMED")
        
    async def _run_scheduler(self):
        """Ana scheduler loop"""
        while self.is_running:
            try:
                # 🆕 PAUSE kontrolü
                if self.is_paused:
                    logger.debug("⏸️  Scheduler paused, waiting...")
                    await asyncio.sleep(10)  # 10 saniye bekle
                    continue
                
                now = datetime.now()
                
                # Günlük tam sync kontrolü
                if self._should_run_full_sync(now):
                    await self._run_full_sync()
                
                # Canlı sync kontrolü (sadece gündüz saatlerinde, 08:00 - 23:00)
                if 8 <= now.hour < 23 and self._should_run_live_sync(now):
                    await self._run_live_sync()
                
                # 1 dakika bekle ve tekrar kontrol et
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Scheduler hatası: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    def _should_run_full_sync(self, now: datetime) -> bool:
        """Tam sync çalışmalı mı?"""
        # ⚠️ STARTUP'TA OTOMATIK ÇALIŞMASIN!
        # İlk sync sadece manuel olarak (admin panel) veya scheduled time'da
        if self.last_full_sync is None:
            # ✅ YENİ MANTIK: Hiç çalışmamışsa, startup sonrası 5 dakika içindeyse
            # ve saat 02:00'ı geçmişse çalıştır (deployment sonrası recovery)
            current_time = now.time()
            
            # Saat 02:00 - 03:00 arası startup'sa hemen çalıştır (scheduled sync kaçmış demektir)
            if self.full_sync_time <= current_time < time(3, 0):
                logger.info("✅ Startup: Scheduled sync time'ı kaçırmışız, şimdi çalıştır")
                return True
            
            # Diğer saatlerde startup'sa, sadece manuel trigger bekle
            logger.info(f"⏳ Startup: İlk sync manuel tetikleme veya yarın {self.full_sync_time.strftime('%H:%M')} bekliyor")
            return False
        
        # Son sync bugün değilse ve saat geçtiyse
        if self.last_full_sync.date() < now.date():
            current_time = now.time()
            return current_time >= self.full_sync_time
        
        return False
    
    def _should_run_live_sync(self, now: datetime) -> bool:
        """Canlı sync çalışmalı mı?"""
        if self.last_live_sync is None:
            return True
        
        elapsed = (now - self.last_live_sync).total_seconds()
        return elapsed >= self.live_sync_interval
    
    async def _run_full_sync(self):
        """Tam veri senkronizasyonu (tüm geçmiş)"""
        try:
            logger.info("🔄 Günlük tam sync başlatılıyor...")
            start_time = datetime.now()
            
            # Sentos client oluştur
            sentos = SentosAPIClient(
                api_url=self.settings.sentos_api_url,
                api_key=self.settings.sentos_api_key,
                api_secret=self.settings.sentos_api_secret
            )
            
            # Data fetcher service oluştur
            fetcher = DataFetcherService(sentos_client=sentos)
            
            # 🆕 ÖNCE ÜRÜN SYNC (RATE LIMIT İÇİN ÇOK ÖNEMLİ!)
            logger.info("📦 Ürün sync başlatılıyor...")
            from database import SessionLocal
            db = SessionLocal()
            try:
                product_count = await asyncio.to_thread(
                    fetcher.sync_products_from_sentos,
                    db=db,
                    max_pages=50  # Max 5000 ürün
                )
                logger.info(f"✅ Ürün sync tamamlandı: {product_count} ürün")
            finally:
                db.close()
            
            # Sonra sipariş sync (7 gün) - SENTOS (Trendyol hariç)
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info("🔵 Sentos sync başlatılıyor (Trendyol hariç)...")
            sentos_result = await asyncio.to_thread(
                fetcher.fetch_and_store_orders,
                start_date=start_date,
                end_date=end_date,
                marketplace=None,
                clear_existing=False
            )
            logger.info(f"✅ Sentos sync tamamlandı: {sentos_result.get('orders_fetched', 0)} sipariş")
            
            # TRENDYOL SYNC (direkt API)
            trendyol_orders = 0
            trendyol_items = 0
            if self.settings.trendyol_supplier_id and self.settings.trendyol_api_key and self.settings.trendyol_api_secret:
                try:
                    logger.info("🟠 Trendyol sync başlatılıyor (direkt API)...")
                    trendyol_client = TrendyolAPIClient(
                        supplier_id=self.settings.trendyol_supplier_id,
                        api_key=self.settings.trendyol_api_key,
                        api_secret=self.settings.trendyol_api_secret
                    )
                    trendyol_fetcher = TrendyolDataFetcherService(trendyol_client=trendyol_client)
                    
                    # Trendyol için de 7 gün
                    trendyol_start = datetime.now() - timedelta(days=7)
                    trendyol_end = datetime.now()
                    
                    trendyol_result = await asyncio.to_thread(
                        trendyol_fetcher.fetch_and_store_trendyol_orders,
                        start_date=trendyol_start,
                        end_date=trendyol_end,
                        statuses=None  # Tüm statusler
                    )
                    trendyol_orders = trendyol_result.get('orders_fetched', 0)
                    trendyol_items = trendyol_result.get('items_stored', 0)
                    logger.info(f"✅ Trendyol sync tamamlandı: {trendyol_orders} sipariş")
                except Exception as e:
                    logger.error(f"❌ Trendyol sync hatası: {e}", exc_info=True)
            else:
                logger.warning("⚠️ Trendyol credentials eksik, Trendyol sync atlandı")
            
            duration = (datetime.now() - start_time).total_seconds()
            self.last_full_sync = datetime.now()
            
            logger.info(f"✅ Günlük tam sync tamamlandı ({duration:.1f}s)")
            logger.info(f"   - Ürünler: {product_count}")
            logger.info(f"   - Sentos Siparişler: {sentos_result.get('orders_fetched', 0)}")
            logger.info(f"   - Trendyol Siparişler: {trendyol_orders}")
            logger.info(f"   - Toplam İtemler: {sentos_result.get('items_stored', 0) + trendyol_items}")
            
        except Exception as e:
            logger.error(f"❌ Tam sync hatası: {e}", exc_info=True)
    
    async def _run_live_sync(self):
        """Canlı veri senkronizasyonu (sadece bugün)"""
        try:
            logger.info("🔴 Canlı sync başlatılıyor (bugünün verisi)...")
            start_time = datetime.now()
            
            # Sadece bugünün verisi
            today = datetime.now().strftime('%Y-%m-%d')
            
            # SENTOS SYNC (Trendyol hariç)
            logger.info("🔵 Sentos canlı sync...")
            sentos = SentosAPIClient(
                api_url=self.settings.sentos_api_url,
                api_key=self.settings.sentos_api_key,
                api_secret=self.settings.sentos_api_secret
            )
            
            # Data fetcher service oluştur ve veriyi çek
            fetcher = DataFetcherService(sentos_client=sentos)
            sentos_result = await asyncio.to_thread(
                fetcher.fetch_and_store_orders,
                start_date=today,
                end_date=today,
                marketplace=None,
                clear_existing=False
            )
            
            # TRENDYOL SYNC (direkt API)
            trendyol_orders = 0
            if self.settings.trendyol_supplier_id and self.settings.trendyol_api_key and self.settings.trendyol_api_secret:
                try:
                    logger.info("🟠 Trendyol canlı sync...")
                    trendyol_client = TrendyolAPIClient(
                        supplier_id=self.settings.trendyol_supplier_id,
                        api_key=self.settings.trendyol_api_key,
                        api_secret=self.settings.trendyol_api_secret
                    )
                    trendyol_fetcher = TrendyolDataFetcherService(trendyol_client=trendyol_client)
                    
                    # Bugün için
                    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    today_end = datetime.now()
                    
                    trendyol_result = await asyncio.to_thread(
                        trendyol_fetcher.fetch_and_store_trendyol_orders,
                        start_date=today_start,
                        end_date=today_end,
                        statuses=None
                    )
                    trendyol_orders = trendyol_result.get('orders_fetched', 0)
                except Exception as e:
                    logger.error(f"❌ Trendyol canlı sync hatası: {e}", exc_info=True)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.last_live_sync = datetime.now()
            
            logger.info(f"✅ Canlı sync tamamlandı ({duration:.1f}s)")
            logger.info(f"   - Sentos: {sentos_result.get('orders_fetched', 0)} sipariş")
            logger.info(f"   - Trendyol: {trendyol_orders} sipariş")
            
        except Exception as e:
            logger.error(f"❌ Canlı sync hatası: {e}", exc_info=True)
    
    async def trigger_full_sync_now(self):
        """Manuel tam sync tetikle"""
        logger.info("🔄 Manuel tam sync tetiklendi")
        await self._run_full_sync()
    
    async def trigger_live_sync_now(self):
        """Manuel canlı sync tetikle"""
        logger.info("🔴 Manuel canlı sync tetiklendi")
        await self._run_live_sync()


# Global instance
_scheduler: Optional[ScheduledSyncService] = None

def get_scheduler() -> ScheduledSyncService:
    """Global scheduler instance'ını al"""
    global _scheduler
    if _scheduler is None:
        _scheduler = ScheduledSyncService()
    return _scheduler
