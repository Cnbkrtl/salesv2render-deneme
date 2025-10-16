"""
Data Fetcher Service - HATASIZ VERİ ÇEKİMİ
Retail filtresi, doğru status mapping, kargo tracking, maliyet hesaplama
OPTIMIZED: Disk-based cache, TTL support, efficient matching
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_

from connectors import SentosAPIClient
from database import Product, SalesOrder, SalesOrderItem, SessionLocal
from app.core import OrderStatus, ItemStatus, Marketplace, SalesChannel
from services.product_cost_cache import ProductCostCache
from services.prefix_discovery import discover_byk_prefixes
from services.cost_match_monitor import get_monitor, reset_monitor
from services.smart_fallback import get_smart_fallback

logger = logging.getLogger(__name__)


def parse_turkish_price(value) -> float:
    """
    Türkiye formatındaki fiyatı parse eder
    
    Örnekler:
    - '1.220,50' -> 1220.50 (binlik noktalı, ondalık virgüllü)
    - '220,00' -> 220.00 (sadece virgüllü)
    - '220.50' -> 220.50 (noktalı - zaten doğru format)
    - 220 -> 220.0 (sayı)
    """
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        value = value.strip()
        
        # Hem nokta hem virgül varsa: Türkiye formatı (1.220,50)
        if '.' in value and ',' in value:
            # Binlik ayracı noktayı kaldır, virgülü noktaya çevir
            value = value.replace('.', '').replace(',', '.')
        # Sadece virgül varsa: Türkiye ondalık (220,50)
        elif ',' in value:
            # Virgülü noktaya çevir
            value = value.replace(',', '.')
        # Sadece nokta varsa: zaten doğru format (220.50) veya yanlış binlik (1.220)
        # Bu durumda olduğu gibi bırak
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def extract_base_sku(variant_sku: Optional[str]) -> Optional[str]:
    """
    Varyant SKU'sundan ana ürün kodunu çıkarır
    
    Örnekler:
    - 'BYK-25K-303760-M41-R15' -> '303760'
    - 'BYK-24K-302793-M51-R15' -> '302793'
    - 'BYK-25Y-304177' -> 'BYK-25Y-304177' (zaten ana SKU)
    - '194938-M41-R15' -> '194938'
    - '322685' -> '322685' (zaten ana SKU)
    
    Args:
        variant_sku: Varyant SKU kodu
        
    Returns:
        Ana ürün SKU kodu veya None
    """
    if not variant_sku:
        return None
    
    variant_sku = variant_sku.strip()
    parts = variant_sku.split('-')
    
    # BYK-25K-303760-M41-R15 formatı (Satış varyantı - 5+ parça)
    if variant_sku.startswith('BYK-') and len(parts) >= 5:
        # BYK-25K-303760-M41-R15 -> 303760 (3. parça)
        return parts[2]
    
    # BYK-25Y-304177 formatı (Product tablosu - 3 parça)
    # Bu zaten ana SKU, olduğu gibi dön
    if variant_sku.startswith('BYK-') and len(parts) == 3:
        return variant_sku
    
    # BYK-24Y-126443-M41-R15 -> 126443 (satış varyantı)
    if variant_sku.startswith('BYK-') and len(parts) == 4:
        return parts[2]
    
    # 194938-M41-R15 formatı (Normal ürün varyantı)
    if '-' in variant_sku and len(parts) >= 3:
        # İlk part genelde ana SKU
        first_part = parts[0]
        # Eğer ilk part sayısal bir kod ise (5+ haneli)
        if first_part.isdigit() and len(first_part) >= 5:
            return first_part
    
    # Hiç tire yoksa zaten ana SKU olabilir
    return variant_sku


def normalize_sku_variants(sku: str) -> list:
    """
    SKU'nun tüm olası normalized varyantlarını döndür
    
    Örnekler:
    - "S00004064" → ["S00004064", "00004064", "4064"]
    - "00004064" → ["00004064", "4064"]
    - "303760" → ["303760"]
    """
    if not sku:
        return []
    
    variants = [sku]  # Orijinal her zaman dahil
    
    # S prefix'ini kaldır
    if sku.startswith('S'):
        without_s = sku[1:]
        variants.append(without_s)
        # S'siz halinin de leading zero'suz hali
        if without_s.isdigit():
            no_zero = without_s.lstrip('0') or '0'
            if no_zero != without_s:
                variants.append(no_zero)
    
    # Leading zero kaldır (numeric SKU'lar için)
    if sku.isdigit():
        no_leading_zero = sku.lstrip('0') or '0'
        if no_leading_zero != sku:
            variants.append(no_leading_zero)
    
    return list(set(variants))  # Benzersiz yap


class DataFetcherService:
    """
    Sentos API'den veri çeker ve database'e kaydeder
    
    OPTIMIZASYONLAR:
    - ✅ Disk-based cost cache (24 saat TTL)
    - ✅ Dictionary lookup O(1)
    - ✅ Sadece satılan ürünlerin maliyetini çek
    - ✅ Batch commit (50 sipariş)
    """
    
    def __init__(self, sentos_client: SentosAPIClient):
        self.sentos = sentos_client
        # Memory cache (DB Product modelleri)
        self.product_cache: Dict[str, Product] = {}
        self.product_cache_by_barcode: Dict[str, Product] = {}
        # Disk cache (Cost bilgileri - 24 saat TTL)
        self.cost_cache = ProductCostCache(cache_dir='data', ttl_hours=24)
        # BYK Prefixes (otomatik keşfedilecek)
        self.byk_prefixes: List[str] = []
        # Monitoring (istatistikler)
        self.monitor = get_monitor()
        # Smart fallback (brand-specific ratios)
        self.smart_fallback = get_smart_fallback()
    
    def fetch_and_store_orders(
        self,
        start_date: str,
        end_date: str,
        marketplace: Optional[str] = None,
        clear_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Siparişleri çeker ve database'e kaydeder
        
        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            marketplace: Opsiyonel marketplace filtresi
            clear_existing: Mevcut verileri temizle
            
        Returns:
            {
                'success': bool,
                'orders_fetched': int,
                'items_stored': int,
                'duration_seconds': float
            }
        """
        start_time = datetime.now()
        db = SessionLocal()
        
        try:
            # Tarihleri parse et
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Mevcut verileri temizle (istenirse)
            if clear_existing:
                self._clear_existing_data(db, start_dt, end_dt, marketplace)
            
            # Ürün cache'ini yükle (maliyet bilgileri için)
            self._load_product_cache(db)
            
            # TÜM STATUS'LARI ÇEK
            # Status listesi: 1=Onay Bekliyor, 2=Onaylandı, 3=Tedarik, 4=Hazırlanıyor, 
            #                 5=Kargoya Verildi, 6=İptal/İade, 99=Teslim Edildi
            all_orders = []
            
            # Tüm status'ları çek (Sentos'tan gelen tüm siparişler)
            status_list = [
                OrderStatus.ONAY_BEKLIYOR,
                OrderStatus.ONAYLANDI,
                OrderStatus.TEDARIK,
                OrderStatus.HAZIRLANIYOR,
                OrderStatus.KARGOYA_VERILDI,
                OrderStatus.IPTAL_IADE,
                OrderStatus.TESLIM_EDILDI
            ]
            
            for status in status_list:
                logger.info(f"Fetching orders with status={status.value} ({status.name})")
                
                orders = self.sentos.get_all_orders(
                    start_date=start_date,
                    end_date=end_date,
                    marketplace=marketplace,
                    status=status.value,
                    page_size=100
                )
                
                logger.info(f"Fetched {len(orders)} orders for status={status.value}")
                all_orders.extend(orders)
            
            # Dedup by order ID
            unique_orders = {order['id']: order for order in all_orders}.values()
            logger.info(f"Total unique orders: {len(unique_orders)}")
            
            # Her siparişi işle
            total_items = 0
            COMMIT_BATCH_SIZE = 50  # Optimize edilmiş batch size
            
            for idx, order in enumerate(unique_orders, 1):
                if idx % 50 == 0:
                    logger.info(f"Processing order {idx}/{len(unique_orders)}...")
                
                # RETAIL FİLTRESİ - Sadece ECOMMERCE
                source = order.get('source', '').upper()
                if source == SalesChannel.RETAIL.value:
                    logger.debug(f"Skipping RETAIL order {order['id']}")
                    continue
                
                # Marketplace kontrolü ve normalize et
                marketplace_name = order.get('source', '')
                normalized_mp = Marketplace.normalize(marketplace_name)
                
                # RETAIL filtresi
                if normalized_mp.upper() == SalesChannel.RETAIL.value:
                    logger.debug(f"Skipping RETAIL order {order['id']}")
                    continue
                
                # Geçersiz marketplace'leri de kaydet (UNKNOWN olarak)
                if normalized_mp == "UNKNOWN" and marketplace_name:
                    logger.warning(f"Unknown marketplace: {marketplace_name}, saving as UNKNOWN")
                
                # Siparişi kaydet
                items_count = self._process_and_store_order(db, order)
                total_items += items_count
                
                # Her COMMIT_BATCH_SIZE siparişte bir commit (optimize edilmiş)
                if idx % COMMIT_BATCH_SIZE == 0:
                    db.commit()
                    logger.debug(f"💾 Committed batch at {idx}/{len(unique_orders)}")
            
            # Final commit
            db.commit()
            
            # 💾 DISK CACHE'İ KAYDET (yeni eklenen maliyet bilgileri)
            self.cost_cache._save_cache()
            logger.info("💾 Cost cache saved to disk")
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # ✅ VALIDATION: Veri doğruluğunu kontrol et
            validation_result = self._validate_fetched_data(
                db, start_date, end_date, len(unique_orders), total_items
            )
            
            # 📊 CACHE STATISTICS
            cache_stats = self.cost_cache.get_cache_stats()
            logger.info(
                f"📊 CACHE STATS: {cache_stats['total_products']} products cached, "
                f"age: {cache_stats['cache_age_hours']:.1f}h"
            )
            
            # 📊 SMART FALLBACK: Calculate brand-specific ratios
            logger.info("📊 Calculating smart fallback ratios...")
            all_items = db.query(SalesOrderItem).all()
            self.smart_fallback.calculate_ratios_from_data(all_items)
            self.smart_fallback.print_report()
            
            # 📊 MONITORING REPORT (Cost Matching Performance)
            logger.info("="*80)
            logger.info("📊 COST MATCHING PERFORMANCE REPORT")
            logger.info("="*80)
            self.monitor.print_report()
            
            logger.info(f"✅ Data fetch completed: {len(unique_orders)} orders, {total_items} items in {duration:.2f}s")
            if validation_result:
                logger.info(f"📊 VALIDATION: {validation_result}")
            
            return {
                'success': True,
                'orders_fetched': len(unique_orders),
                'items_stored': total_items,
                'duration_seconds': duration,
                'validation': validation_result,
                'cache_stats': cache_stats
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Data fetch failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            db.close()
    
    def _process_and_store_order(self, db: Session, order: Dict) -> int:
        """Tek siparişi işler ve kaydeder"""
        
        # Order bilgileri
        sentos_order_id = order['id']
        order_code = order.get('order_code', '')
        order_date_str = order.get('order_date', '')
        marketplace = Marketplace.normalize(order.get('source', ''))
        shop = order.get('shop', '')
        order_status = order.get('status', OrderStatus.ONAY_BEKLIYOR.value)
        
        # Parse order date
        try:
            order_date = datetime.strptime(order_date_str, "%Y-%m-%d %H:%M:%S")
        except:
            order_date = datetime.now()
        
        # Financial - ORDER LEVEL
        order_total = parse_turkish_price(order.get('total', 0))
        shipping_total = parse_turkish_price(order.get('shipping_total', 0))
        carrying_charge = parse_turkish_price(order.get('carrying_charge', 0))
        service_fee = parse_turkish_price(order.get('service_fee', 0))
        
        # Kargo
        cargo_provider = order.get('cargo_provider', '')
        cargo_number = order.get('cargo_number', '')
        
        # Fatura
        has_invoice = order.get('has_invoice', 'no')
        invoice_type = order.get('invoice_type', '')
        invoice_number = order.get('invoice_number', '')
        
        # SalesOrder kaydet veya güncelle
        sales_order = db.query(SalesOrder).filter(
            SalesOrder.sentos_order_id == sentos_order_id
        ).first()
        
        if not sales_order:
            sales_order = SalesOrder(
                sentos_order_id=sentos_order_id,
                order_code=order_code,
                order_date=order_date,
                marketplace=marketplace,
                shop=shop,
                order_status=order_status,
                order_total=order_total,
                shipping_total=shipping_total,
                carrying_charge=carrying_charge,
                service_fee=service_fee,
                cargo_provider=cargo_provider,
                cargo_number=cargo_number,
                has_invoice=has_invoice,
                invoice_type=invoice_type,
                invoice_number=invoice_number
            )
            db.add(sales_order)
            db.flush()  # Get ID
        else:
            # Update
            sales_order.order_status = order_status
            sales_order.order_total = order_total
            sales_order.shipping_total = shipping_total
            sales_order.updated_at = datetime.now()
        
        # Items işle
        items = order.get('lines', order.get('items', []))
        items_count = 0
        
        for item in items:
            was_inserted = self._process_and_store_item(db, sales_order, order, item, order_status)
            if was_inserted:  # Sadece INSERT edilen itemları say
                items_count += 1
        
        return items_count
    
    def _process_and_store_item(
        self,
        db: Session,
        sales_order: SalesOrder,
        order: Dict,
        item: Dict,
        order_status: int
    ):
        """Sipariş kalemini işler ve kaydeder"""
        
        sentos_order_id = order['id']
        sentos_item_id = item.get('id', 0)
        product_sku = item.get('sku', 'unknown')
        
        # UNIQUE KEY FIX: order_id + item_id + SKU kullan
        # Sentos bazen aynı item_id'yi farklı SKU'lar için kullanıyor!
        if sentos_item_id == 0:
            # item_id=0 ise, SKU + sequence kullan
            existing_count = db.query(SalesOrderItem).filter(
                SalesOrderItem.order_id == sales_order.id,
                SalesOrderItem.product_sku == product_sku
            ).count()
            unique_key = f"{sentos_order_id}_{product_sku}_{existing_count}"
            
            # ⚠️ COLLISION WARNING - item_id=0 collision riski
            if existing_count > 0:
                logger.warning(
                    f"⚠️ COLLISION RISK: item_id=0, SKU={product_sku}, "
                    f"order={sentos_order_id}, sequence={existing_count}"
                )
        else:
            # item_id varsa ama aynı ID farklı SKU'lar için kullanılabilir!
            unique_key = f"{sentos_order_id}_{sentos_item_id}_{product_sku}"
        
        # Product info
        product_name = item.get('name', '')
        product_sku = item.get('sku', '')
        barcode = item.get('barcode', '')
        color = item.get('color', '')
        
        model = item.get('model', {})
        model_name = model.get('name', '') if isinstance(model, dict) else ''
        model_value = model.get('value', '') if isinstance(model, dict) else ''
        
        # Item status - GERÇEK İADE TESPİTİ
        item_status = item.get('status', ItemStatus.ACCEPTED.value)
        
        # Quantities
        quantity = int(item.get('quantity', 0))
        
        # Financial
        raw_price = item.get('price', 0)
        raw_amount = item.get('amount', 0)
        unit_price = parse_turkish_price(raw_price)
        item_amount = parse_turkish_price(raw_amount)
        
        # ⚠️ VALIDATION: Price parsing kontrolü
        if raw_price and unit_price == 0.0:
            logger.error(
                f"❌ PRICE PARSE ERROR: raw_price={raw_price}, "
                f"SKU={product_sku}, order={sentos_order_id}"
            )
        if raw_amount and item_amount == 0.0:
            logger.error(
                f"❌ AMOUNT PARSE ERROR: raw_amount={raw_amount}, "
                f"SKU={product_sku}, order={sentos_order_id}"
            )
        
        # Cost - Ürün maliyetini bul (KDV'li) - OPTIMIZED with CACHE
        # SKU matching: Varyant SKU'sundan ana SKU'yu çıkar
        base_sku = extract_base_sku(product_sku)
        unit_cost_with_vat = 0.0
        cost_source = "UNKNOWN"
        
        # ⚡ ÖNCE DISK CACHE'DEN DENE (24 saat TTL)
        cached_cost = self.cost_cache.get_cached_cost(product_sku)
        if cached_cost:
            unit_cost_with_vat = cached_cost['cost']
            cost_source = "DISK_CACHE"
            # Monitoring: Cache hit
            self.monitor.record_match('cache', product_sku)
            # Cache'den geldi, debug log'a gerek yok (çok fazla log olur)
        else:
            # Cache miss - Memory cache'den bul ve disk cache'e ekle
            
            # 1. Önce varyant SKU ile doğrudan dene
            if product_sku and product_sku in self.product_cache:
                product = self.product_cache[product_sku]
                unit_cost_with_vat = product.purchase_price_with_vat
                cost_source = "DIRECT"
                # Monitoring: Direct match
                self.monitor.record_match('direct', product_sku)
                logger.debug(f"✅ COST DIRECT: {product_sku} = {unit_cost_with_vat:.2f} TL")
                # Disk cache'e ekle
                self.cost_cache.add_to_cache(
                    sku=product_sku,
                    cost=unit_cost_with_vat,
                    barcode=product.barcode,
                    name=product.name
                )
            
            # 2. Ana SKU ile dene
            elif base_sku and base_sku in self.product_cache:
                product = self.product_cache[base_sku]
                unit_cost_with_vat = product.purchase_price_with_vat
                cost_source = "BASE_MATCH"
                # Monitoring: Base SKU match
                self.monitor.record_match('base_sku', product_sku, base_sku)
                logger.debug(f"✅ COST MATCHED: {product_sku} → {base_sku} = {unit_cost_with_vat:.2f} TL")
                # Disk cache'e ekle (varyant SKU ile)
                self.cost_cache.add_to_cache(
                    sku=product_sku,
                    cost=unit_cost_with_vat,
                    barcode=barcode,
                    name=product_name
                )
            
            # 3. BYK ürünleri için alternatif formatları dene (OTOMATIK KEŞİF!)
            elif product_sku and product_sku.startswith('BYK-') and base_sku:
                # BYK-25K-303760-M41-R15 → BYK-25K-303760 veya BYK-25Y-303760 dene
                # Otomatik keşfedilen prefix'ler (sıklığa göre sıralı)
                # BYK-24Y en sık (%30.4), sonra BYK-23Y (%20.8), ...
                for prefix in self.byk_prefixes:
                    alt_sku = f"{prefix}-{base_sku}"
                    if alt_sku in self.product_cache:
                        product = self.product_cache[alt_sku]
                        unit_cost_with_vat = product.purchase_price_with_vat
                        cost_source = "BYK_MATCH"
                        # Monitoring: BYK prefix match (hangi prefix başarılı?)
                        self.monitor.record_match('byk_prefix', product_sku, alt_sku, prefix=prefix)
                        logger.debug(f"✅ COST BYK_MATCHED: {product_sku} → {alt_sku} = {unit_cost_with_vat:.2f} TL")
                        # Disk cache'e ekle
                        self.cost_cache.add_to_cache(
                            sku=product_sku,
                            cost=unit_cost_with_vat,
                            barcode=barcode,
                            name=product_name
                        )
                        break
            
            # 4. BARCODE ile eşleşme dene
            if unit_cost_with_vat == 0.0 and barcode:
                # Önce disk cache'de barcode ara
                cached_by_barcode = self.cost_cache.get_cached_cost_by_barcode(barcode)
                if cached_by_barcode:
                    unit_cost_with_vat = cached_by_barcode['cost']
                    cost_source = "BARCODE_CACHE"
                # Yoksa memory cache'den
                elif barcode in self.product_cache_by_barcode:
                    product = self.product_cache_by_barcode[barcode]
                    unit_cost_with_vat = product.purchase_price_with_vat
                    cost_source = "BARCODE_MATCH"
                    # Monitoring: Barcode match
                    self.monitor.record_match('barcode', product_sku, product.sku)
                    logger.debug(f"✅ COST BARCODE_MATCHED: {barcode} → {product.sku} = {unit_cost_with_vat:.2f} TL")
                    # Disk cache'e ekle
                    self.cost_cache.add_to_cache(
                        sku=product_sku,
                        cost=unit_cost_with_vat,
                        barcode=barcode,
                        name=product_name
                    )
            
            # 5. SKU Normalizasyon (S prefix, leading zeros)
            if unit_cost_with_vat == 0.0 and product_sku:
                sku_variants = normalize_sku_variants(product_sku)
                for variant in sku_variants:
                    if variant != product_sku and variant in self.product_cache:
                        product = self.product_cache[variant]
                        unit_cost_with_vat = product.purchase_price_with_vat
                        cost_source = "NORMALIZED_MATCH"
                        # Monitoring: Normalized match
                        self.monitor.record_match('normalize', product_sku, variant)
                        logger.debug(f"✅ COST NORMALIZED: {product_sku} → {variant} = {unit_cost_with_vat:.2f} TL")
                        # Disk cache'e ekle
                        self.cost_cache.add_to_cache(
                            sku=product_sku,
                            cost=unit_cost_with_vat,
                            barcode=barcode,
                            name=product_name
                        )
                        break
        
        # 6. Hala bulunamadıysa → ÖNCE SENTOS API'DEN ÇEKMEYİ DENE
        if unit_cost_with_vat == 0.0 and base_sku:
            try:
                # Base SKU ile Sentos API'den ürünü çek (barcode parametresi ile)
                logger.info(f"🔍 Ürün database'de yok, Sentos API'den çekiliyor: {base_sku}")
                product_data = self.sentos.get_product_by_sku(base_sku, barcode=barcode)
                
                if product_data:
                    # Ürünü database'e ekle (görselleri ile birlikte!)
                    self._sync_product(db, product_data)
                    db.flush()  # Database'e commit
                    
                    # Cache'leri yenile
                    product = db.query(Product).filter(Product.sku == base_sku).first()
                    if product:
                        self.product_cache[base_sku] = product
                        if product.barcode:
                            self.product_cache_by_barcode[product.barcode] = product
                        
                        # Cost'u al
                        unit_cost_with_vat = product.purchase_price_with_vat
                        cost_source = "API_FETCHED"
                        logger.info(f"✅ Ürün Sentos'tan çekildi ve eklendi: {base_sku} = {unit_cost_with_vat:.2f} TL")
                        
                        # Cache'e ekle
                        self.cost_cache.add_to_cache(
                            sku=product_sku,
                            cost=unit_cost_with_vat,
                            barcode=product.barcode,
                            name=product.name
                        )
            except Exception as e:
                logger.warning(f"⚠️ Sentos API'den ürün çekilemedi ({base_sku}): {e}")
        
        # 7. Hala bulunamadıysa fallback (SMART FALLBACK - brand-based)
        if unit_cost_with_vat == 0.0:
            # Smart fallback: brand-specific ratio or default 0.70
            unit_cost_with_vat, fallback_source = self.smart_fallback.get_fallback_cost(
                unit_price=unit_price,
                product_sku=product_sku
            )
            cost_source = f"FALLBACK_{fallback_source}"
            # Monitoring: Fallback (record unmatched pattern)
            self.monitor.record_match('fallback', product_sku)
            self.monitor.record_unmatched(product_sku)
            logger.warning(
                f"⚠️ COST FALLBACK: SKU={product_sku}, base={base_sku} "
                f"→ {unit_cost_with_vat:.2f} TL ({fallback_source})"
            )
            # Fallback'i de cache'e ekle (sonraki çalıştırmalarda hemen bulunur)
            self.cost_cache.add_to_cache(
                sku=product_sku,
                cost=unit_cost_with_vat,
                barcode=barcode,
                name=product_name
            )
        
        total_cost_with_vat = unit_cost_with_vat * quantity
        
        # Commission (marketplace-specific) - Sonra hesaplanabilir
        commission_rate = 0.0
        commission_amount = 0.0
        
        # Calculated flags
        is_return = (item_status == ItemStatus.REJECTED.value)
        is_cancelled = (order_status == OrderStatus.IPTAL_IADE.value)
        
        # SalesOrderItem kaydet veya güncelle
        sales_item = db.query(SalesOrderItem).filter(
            SalesOrderItem.unique_key == unique_key
        ).first()
        
        is_new_item = False  # Track if this is a new insert
        
        if not sales_item:
            # ✅ NEW INSERT
            sales_item = SalesOrderItem(
                order_id=sales_order.id,
                sentos_order_id=sentos_order_id,
                sentos_item_id=sentos_item_id,
                unique_key=unique_key,
                product_name=product_name,
                product_sku=product_sku,
                barcode=barcode,
                color=color,
                model_name=model_name,
                model_value=model_value,
                item_status=item_status,
                quantity=quantity,
                unit_price=unit_price,
                item_amount=item_amount,
                unit_cost_with_vat=unit_cost_with_vat,
                total_cost_with_vat=total_cost_with_vat,
                commission_rate=commission_rate,
                commission_amount=commission_amount,
                is_return=is_return,
                is_cancelled=is_cancelled
            )
            db.add(sales_item)
            db.flush()  # Flush to get ID immediately
            is_new_item = True  # This is a new insert
            
            logger.debug(f"✅ INSERT: unique_key={unique_key}, SKU={product_sku}, amount={item_amount:.2f}")
        else:
            # 🔄 UPDATE EXISTING - Aynı sipariş farklı status'larda gelebilir
            old_amount = sales_item.item_amount
            old_status = sales_item.item_status
            
            # Update existing
            sales_item.item_status = item_status
            sales_item.quantity = quantity
            sales_item.unit_price = unit_price
            sales_item.item_amount = item_amount
            sales_item.unit_cost_with_vat = unit_cost_with_vat
            sales_item.total_cost_with_vat = total_cost_with_vat
            sales_item.is_return = is_return
            sales_item.is_cancelled = is_cancelled
            sales_item.updated_at = datetime.now()
            
            # ⚠️ LOG SIGNIFICANT CHANGES
            if abs(old_amount - item_amount) > 0.01:
                logger.warning(
                    f"⚠️ AMOUNT CHANGED: unique_key={unique_key}, "
                    f"old={old_amount:.2f} → new={item_amount:.2f}"
                )
            if old_status != item_status:
                logger.info(
                    f"🔄 STATUS CHANGED: unique_key={unique_key}, "
                    f"old={old_status} → new={item_status}"
                )
        
        return is_new_item  # Return True if inserted, False if updated
    
    def _load_product_cache(self, db: Session):
        """
        Ürün cache'ini yükler - OPTIMIZED
        
        İki seviyeli cache:
        1. Memory cache: Product model instance'ları (SKU matching için)
        2. Disk cache: Cost bilgileri (24 saat TTL, kalıcı)
        """
        # 1. Memory cache (SKU matching için tüm ürünler)
        products = db.query(Product).all()
        self.product_cache = {p.sku: p for p in products if p.sku}
        self.product_cache_by_barcode = {p.barcode: p for p in products if p.barcode}
        
        logger.info(
            f"📦 Memory cache loaded: {len(self.product_cache)} products "
            f"({len(self.product_cache_by_barcode)} with barcodes)"
        )
        
        # 2. Disk cache güncelle (sadece cost bilgileri)
        updated = self.cost_cache.update_from_db_products(products)
        
        # 3. BYK Prefix'leri otomatik keşfet (YENI!)
        self.byk_prefixes = discover_byk_prefixes(self.product_cache)
        logger.info(
            f"🔍 BYK Prefixes: {len(self.byk_prefixes)} discovered "
            f"(top 3: {', '.join(self.byk_prefixes[:3])})"
        )
        
        # 4. Cache istatistiklerini göster
        stats = self.cost_cache.get_cache_stats()
        logger.info(
            f"💾 Disk cache: {stats['total_products']} products, "
            f"age: {stats['cache_age_hours']:.1f}h, "
            f"valid: {stats['cache_valid']}"
        )
    
    def _validate_fetched_data(
        self,
        db: Session,
        start_date: str,
        end_date: str,
        expected_orders: int,
        expected_items: int
    ) -> Dict[str, Any]:
        """
        Çekilen verinin doğruluğunu kontrol eder
        
        Returns:
            {
                'db_orders': int,
                'db_items': int,
                'match_orders': bool,
                'match_items': bool,
                'warnings': List[str]
            }
        """
        try:
            # Tarihleri parse et
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Database'deki order sayısı
            db_orders = db.query(SalesOrder).filter(
                and_(
                    SalesOrder.order_date >= start_dt,
                    SalesOrder.order_date < end_dt + timedelta(days=1)
                )
            ).count()
            
            # Database'deki item sayısı
            db_items = db.query(SalesOrderItem).join(SalesOrder).filter(
                and_(
                    SalesOrder.order_date >= start_dt,
                    SalesOrder.order_date < end_dt + timedelta(days=1)
                )
            ).count()
            
            warnings = []
            
            # Order count kontrolü
            if db_orders != expected_orders:
                warnings.append(
                    f"⚠️ ORDER MISMATCH: Expected {expected_orders}, found {db_orders} in DB"
                )
            
            # Item count kontrolü (INSERT edilen vs DB'deki toplam)
            # NOT: expected_items sadece yeni INSERT'ler, db_items tüm itemlar
            if db_items < expected_items:
                warnings.append(
                    f"⚠️ ITEM MISMATCH: Expected at least {expected_items}, found {db_items} in DB"
                )
            
            # Duplicate unique_key kontrolü
            duplicate_check = db.execute("""
                SELECT unique_key, COUNT(*) as cnt
                FROM sales_order_items
                GROUP BY unique_key
                HAVING COUNT(*) > 1
            """).fetchall()
            
            if duplicate_check:
                warnings.append(
                    f"❌ DUPLICATE UNIQUE_KEYS: {len(duplicate_check)} collisions detected!"
                )
                for dup in duplicate_check[:5]:  # İlk 5 collision
                    logger.error(f"❌ COLLISION: unique_key={dup[0]}, count={dup[1]}")
            
            # Sıfır fiyatlı itemlar
            zero_price_items = db.query(SalesOrderItem).filter(
                SalesOrderItem.item_amount == 0.0
            ).count()
            
            if zero_price_items > 0:
                warnings.append(
                    f"⚠️ ZERO PRICE: {zero_price_items} items with amount=0.0"
                )
            
            return {
                'db_orders': db_orders,
                'db_items': db_items,
                'expected_orders': expected_orders,
                'expected_items': expected_items,
                'match_orders': db_orders == expected_orders,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {'error': str(e)}
    
    def sync_products_from_sentos(self, db: Session, max_pages: int = 10):
        """
        Sentos'tan ürünleri çeker ve maliyet bilgilerini günceller
        Cache'i temizler ve fresh data ile yeniden oluşturur
        """
        logger.info(f"🔄 Syncing products from Sentos API (max_pages={max_pages})...")
        
        # 🆕 Cache'i temizle - fresh start için
        logger.info("🗑️  Clearing old cache for fresh sync...")
        self.cost_cache.clear_cache()
        
        page = 1
        total_synced = 0
        
        while page <= max_pages:
            logger.info(f"📄 Fetching page {page}...")
            result = self.sentos.get_products_bulk(page=page, size=100)
            products = result.get('products', [])
            total_count = result.get('total', 0)
            total_pages = result.get('total_pages', 1)
            
            logger.info(f"📊 Page {page}/{total_pages} - Found {len(products)} products (Total: {total_count})")
            
            if not products:
                logger.warning(f"⚠️ No products found on page {page}")
                break
            
            for product_data in products:
                self._sync_product(db, product_data)
                total_synced += 1
            
            db.commit()
            logger.info(f"💾 Committed page {page} - Total synced so far: {total_synced}")
            
            # Eğer son sayfaya ulaştıysak dur
            if page >= total_pages:
                logger.info(f"✅ Reached last page ({page}/{total_pages})")
                break
            
            page += 1
        
        # 🆕 Sync bitti, yeni cache'i oluştur
        logger.info("💾 Rebuilding cache with fresh data...")
        self._rebuild_cache_from_db(db)
        
        logger.info(f"✅ Synced {total_synced} products from {page} page(s)")
        logger.info(f"✅ Cache rebuilt with {total_synced} products")
        return total_synced
    
    def _rebuild_cache_from_db(self, db: Session):
        """Database'deki tüm ürünlerden cache'i yeniden oluştur"""
        all_products = db.query(Product).all()
        
        logger.info(f"🔄 Loading {len(all_products)} products into cache...")
        
        for product in all_products:
            # Cost cache'e ekle
            self.cost_cache.add_to_cache(
                sku=product.sku,
                cost=product.purchase_price_with_vat,
                barcode=product.barcode,
                name=product.name
            )
            
            # Memory cache'e ekle
            self.product_cache[product.sku] = product
            if product.barcode:
                self.product_cache_by_barcode[product.barcode] = product
        
        # Disk'e kaydet
        self.cost_cache._save_cache()
        logger.info(f"✅ Cache rebuilt: {len(all_products)} products loaded")
    
    def _sync_product(self, db: Session, product_data: Dict):
        """Tek ürünü sync eder"""
        sentos_product_id = product_data['id']
        sku = product_data.get('sku', '')
        
        if not sku:
            return
        
        # Maliyet bilgileri - Türkiye formatından parse et
        purchase_price = parse_turkish_price(product_data.get('purchase_price', 0))
        vat_rate = int(product_data.get('vat_rate', 10))
        purchase_price_with_vat = purchase_price * (1 + vat_rate / 100)
        
        # Ürünü bul veya oluştur
        product = db.query(Product).filter(Product.sku == sku).first()
        
        # Extract image - ilk görseli al
        image_url = None
        if 'images' in product_data and isinstance(product_data['images'], list) and len(product_data['images']) > 0:
            first_image = product_data['images'][0]
            if isinstance(first_image, dict):
                image_url = first_image.get('url') or first_image.get('image_url')
            elif isinstance(first_image, str):
                image_url = first_image
        
        if not product:
            product = Product(
                sentos_product_id=sentos_product_id,
                sku=sku,
                name=product_data.get('name', ''),
                brand=product_data.get('brand', ''),
                barcode=product_data.get('barcode', ''),
                image=image_url,
                purchase_price=purchase_price,
                vat_rate=vat_rate,
                purchase_price_with_vat=purchase_price_with_vat,
                sale_price=parse_turkish_price(product_data.get('sale_price', 0))
            )
            db.add(product)
        else:
            # Update
            product.image = image_url
            product.purchase_price = purchase_price
            product.vat_rate = vat_rate
            product.purchase_price_with_vat = purchase_price_with_vat
            product.updated_at = datetime.now()
    
    def _clear_existing_data(
        self,
        db: Session,
        start_dt: datetime,
        end_dt: datetime,
        marketplace: Optional[str] = None
    ):
        """Belirtilen tarih aralığındaki verileri temizler"""
        
        # Orders'ı bul
        query = db.query(SalesOrder).filter(
            and_(
                SalesOrder.order_date >= start_dt,
                SalesOrder.order_date < end_dt + timedelta(days=1)
            )
        )
        
        if marketplace:
            query = query.filter(SalesOrder.marketplace == marketplace)
        
        order_ids = [o.id for o in query.all()]
        
        if order_ids:
            # Items'ları sil
            deleted_items = db.query(SalesOrderItem).filter(
                SalesOrderItem.order_id.in_(order_ids)
            ).delete(synchronize_session=False)
            
            # Orders'ları sil
            deleted_orders = db.query(SalesOrder).filter(
                SalesOrder.id.in_(order_ids)
            ).delete(synchronize_session=False)
            
            db.commit()
            
            logger.info(f"Cleared {deleted_orders} orders and {deleted_items} items")
