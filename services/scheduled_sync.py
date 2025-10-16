"""
Scheduled Data Sync Service
Otomatik veri senkronizasyonu için background scheduler
"""
import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Optional
import threading

from services.data_fetcher import fetch_and_store_sales_data
from connectors.sentos_client import SentosAPIClient
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
        
    async def _run_scheduler(self):
        """Ana scheduler loop"""
        while self.is_running:
            try:
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
        # Bugün hiç çalışmadıysa ve saat geçtiyse
        if self.last_full_sync is None:
            current_time = now.time()
            return current_time >= self.full_sync_time
        
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
            
            # 90 gün geriye git
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Sentos client oluştur
            sentos = SentosAPIClient(
                api_url=self.settings.sentos_api_url,
                api_key=self.settings.sentos_api_key,
                api_secret=self.settings.sentos_api_secret
            )
            
            # Veriyi çek ve kaydet
            result = await asyncio.to_thread(
                fetch_and_store_sales_data,
                sentos_client=sentos,
                start_date=start_date,
                end_date=end_date,
                force_product_sync=True  # Ürünleri de güncelle
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            self.last_full_sync = datetime.now()
            
            logger.info(f"✅ Günlük tam sync tamamlandı ({duration:.1f}s)")
            logger.info(f"   - Siparişler: {result.get('orders_processed', 0)}")
            logger.info(f"   - Ürünler: {result.get('products_synced', 0)}")
            
        except Exception as e:
            logger.error(f"❌ Tam sync hatası: {e}", exc_info=True)
    
    async def _run_live_sync(self):
        """Canlı veri senkronizasyonu (sadece bugün)"""
        try:
            logger.info("🔴 Canlı sync başlatılıyor (bugünün verisi)...")
            start_time = datetime.now()
            
            # Sadece bugünün verisi
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Sentos client oluştur
            sentos = SentosAPIClient(
                api_url=self.settings.sentos_api_url,
                api_key=self.settings.sentos_api_key,
                api_secret=self.settings.sentos_api_secret
            )
            
            # Veriyi çek ve kaydet (ürün sync'i yok)
            result = await asyncio.to_thread(
                fetch_and_store_sales_data,
                sentos_client=sentos,
                start_date=today,
                end_date=today,
                force_product_sync=False  # Ürünleri güncelleme
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            self.last_live_sync = datetime.now()
            
            logger.info(f"✅ Canlı sync tamamlandı ({duration:.1f}s)")
            logger.info(f"   - Siparişler: {result.get('orders_processed', 0)}")
            
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
