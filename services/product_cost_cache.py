"""
Product Cost Cache Manager - Disk tabanlı cache sistemi
Cache TTL: 24 saat (configurable)
"""
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class ProductCostCache:
    """
    Ürün maliyet cache'i - Disk tabanlı, TTL destekli
    
    Özellikler:
    - 24 saatlik TTL (otomatik yenileme)
    - SKU ve Barcode indeksli
    - Disk'te kalıcı (restart'ta kaybolmaz)
    - Sadece satılan ürünleri saklar (memory efficient)
    """
    
    def __init__(self, cache_dir: str = 'data', ttl_hours: int = 24):
        """
        Args:
            cache_dir: Cache dosyasının konumu
            ttl_hours: Cache geçerlilik süresi (saat)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.cache_file = self.cache_dir / 'product_cost_cache.json'
        self.ttl_seconds = ttl_hours * 3600
        
        # Cache structure: {sku: {cost, barcode, name, timestamp}}
        self.cache: Dict[str, Dict] = {}
        self.cache_by_barcode: Dict[str, Dict] = {}
        
        self._load_cache()
    
    def _load_cache(self):
        """Cache'i disk'ten yükler"""
        if not self.cache_file.exists():
            logger.info("📦 Cache dosyası bulunamadı, yeni cache oluşturulacak")
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cache_timestamp = data.get('timestamp', 0)
            cache_age = time.time() - cache_timestamp
            
            # TTL kontrolü
            if cache_age > self.ttl_seconds:
                logger.warning(
                    f"⏰ Cache expired ({cache_age/3600:.1f} saat). "
                    f"Yeni cache oluşturulacak."
                )
                return
            
            # Cache'i yükle
            self.cache = data.get('products', {})
            
            # Barcode indeksini oluştur
            self.cache_by_barcode = {
                product['barcode']: product
                for product in self.cache.values()
                if product.get('barcode')
            }
            
            logger.info(
                f"✅ Cache yüklendi: {len(self.cache)} ürün "
                f"({len(self.cache_by_barcode)} barcode'lu), "
                f"yaş: {cache_age/3600:.1f} saat"
            )
            
        except Exception as e:
            logger.error(f"❌ Cache yüklenemedi: {e}")
            self.cache = {}
            self.cache_by_barcode = {}
    
    def _save_cache(self):
        """Cache'i disk'e kaydeder"""
        try:
            data = {
                'timestamp': time.time(),
                'created_at': datetime.now().isoformat(),
                'total_products': len(self.cache),
                'products': self.cache
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Cache kaydedildi: {len(self.cache)} ürün")
            
        except Exception as e:
            logger.error(f"❌ Cache kaydedilemedi: {e}")
    
    def get_cached_cost(self, sku: str) -> Optional[Dict]:
        """
        SKU için cache'den maliyet getirir
        
        Returns:
            {
                'cost': float,
                'barcode': str,
                'name': str,
                'sku': str
            } veya None
        """
        return self.cache.get(sku)
    
    def get_cached_cost_by_barcode(self, barcode: str) -> Optional[Dict]:
        """Barcode için cache'den maliyet getirir"""
        return self.cache_by_barcode.get(barcode)
    
    def add_to_cache(self, sku: str, cost: float, barcode: str = None, name: str = None):
        """
        Cache'e yeni ürün ekler
        
        Args:
            sku: Ürün SKU kodu
            cost: Birim maliyet (KDV dahil)
            barcode: Ürün barkodu
            name: Ürün adı
        """
        product_data = {
            'cost': float(cost),
            'barcode': barcode,
            'name': name,
            'sku': sku,
            'updated_at': datetime.now().isoformat()
        }
        
        self.cache[sku] = product_data
        
        if barcode:
            self.cache_by_barcode[barcode] = product_data
    
    def update_from_db_products(self, db_products: List) -> int:
        """
        Database'den gelen Product listesi ile cache'i günceller
        
        Args:
            db_products: Product model instance'ları
            
        Returns:
            Eklenen/güncellenen ürün sayısı
        """
        updated_count = 0
        
        for product in db_products:
            if not product.sku:
                continue
            
            # Mevcut cache'deki değer
            existing = self.cache.get(product.sku)
            
            # Cost değişmişse veya yeni ürünse güncelle
            product_cost = product.purchase_price_with_vat or 0.0
            
            if not existing or existing.get('cost') != product_cost:
                self.add_to_cache(
                    sku=product.sku,
                    cost=product_cost,
                    barcode=product.barcode,
                    name=product.name
                )
                updated_count += 1
        
        if updated_count > 0:
            self._save_cache()
            logger.info(f"🔄 Cache güncellendi: {updated_count} ürün")
        
        return updated_count
    
    def get_missing_skus(self, required_skus: Set[str]) -> Set[str]:
        """
        Cache'de olmayan SKU'ları bulur
        
        Args:
            required_skus: İhtiyaç duyulan SKU listesi
            
        Returns:
            Cache'de olmayan SKU'lar
        """
        return required_skus - set(self.cache.keys())
    
    def get_cache_stats(self) -> Dict:
        """Cache istatistiklerini döner"""
        cache_age = 0
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cache_age = time.time() - data.get('timestamp', 0)
            except:
                pass
        
        return {
            'total_products': len(self.cache),
            'products_with_barcode': len(self.cache_by_barcode),
            'cache_age_hours': cache_age / 3600,
            'cache_file': str(self.cache_file),
            'cache_valid': cache_age < self.ttl_seconds
        }
    
    def clear_cache(self):
        """Cache'i temizler (disk ve memory)"""
        self.cache = {}
        self.cache_by_barcode = {}
        
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("🗑️ Cache temizlendi")
