"""
Trendyol Data Fetcher Service
Trendyol API'den sipariş verilerini çeker ve database'e kaydeder
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from connectors.trendyol_client import TrendyolAPIClient
from database import Product, SalesOrder, SalesOrderItem, SessionLocal
from app.core import OrderStatus
from services.product_cost_cache import ProductCostCache

logger = logging.getLogger(__name__)


class TrendyolDataFetcherService:
    """
    Trendyol API'den veri çeker ve database'e kaydeder
    """
    
    def __init__(self, trendyol_client: TrendyolAPIClient):
        self.trendyol = trendyol_client
        # Product cache (maliyet bilgileri için)
        self.product_cache: Dict[str, Product] = {}
        # Disk cache (Cost bilgileri - 24 saat TTL)
        self.cost_cache = ProductCostCache(cache_dir='data', ttl_hours=24)
    
    def fetch_and_store_trendyol_orders(
        self,
        start_date: str,
        end_date: str,
        statuses: Optional[List[str]] = None,
        clear_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Trendyol siparişlerini çeker ve database'e kaydeder
        
        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            statuses: Sipariş statüleri (None = tümü)
            clear_existing: Mevcut Trendyol verilerini temizle
        
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
            # Tarihleri parse et (string veya datetime kabul et)
            if isinstance(start_date, str):
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                start_dt = start_date
            
            if isinstance(end_date, str):
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            else:
                end_dt = end_date
            
            # Mevcut Trendyol verilerini temizle (istenirse)
            if clear_existing:
                self._clear_trendyol_data(db, start_dt, end_dt)
            
            # Product cache yükle
            self._load_product_cache(db)
            
            # Trendyol siparişlerini çek
            logger.info(f"📦 Fetching Trendyol orders: {start_date} to {end_date}")
            
            packages = self.trendyol.get_orders_by_date_range(
                start_date=start_dt,
                end_date=end_dt,
                statuses=statuses
            )
            
            logger.info(f"✅ Fetched {len(packages)} Trendyol packages from API")
            
            # ⚠️ ÖNEMLİ: API'deki tarih filtresi PackageLastModifiedDate kullanıyor
            # Biz orderDate (sipariş oluşturma tarihi) ile filtrelemek istiyoruz
            filtered_packages = []
            for package in packages:
                order_date_ms = package.get('orderDate', 0)
                if order_date_ms:
                    order_date = datetime.fromtimestamp(order_date_ms / 1000)
                    # Tarih aralığında mı kontrol et
                    if start_dt <= order_date <= end_dt:
                        filtered_packages.append(package)
                else:
                    # orderDate yoksa ekle (güvenli taraf)
                    filtered_packages.append(package)
            
            logger.info(f"✅ Filtered to {len(filtered_packages)} packages by orderDate (was {len(packages)})")
            
            # Database'e kaydet
            orders_count = 0
            items_count = 0
            
            for package in filtered_packages:
                try:
                    items = self._process_and_store_trendyol_package(db, package)
                    orders_count += 1
                    items_count += items
                    
                    # Her 50 sipariş commit et
                    if orders_count % 50 == 0:
                        db.commit()
                        logger.info(f"💾 Committed {orders_count} orders, {items_count} items")
                
                except Exception as e:
                    logger.error(f"❌ Error processing package {package.get('id')}: {e}")
                    continue
            
            # Final commit
            db.commit()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"🎉 Trendyol sync completed!")
            logger.info(f"   - Orders: {orders_count}")
            logger.info(f"   - Items: {items_count}")
            logger.info(f"   - Duration: {duration:.1f}s")
            
            return {
                'success': True,
                'orders_fetched': orders_count,
                'items_stored': items_count,
                'duration_seconds': duration
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Trendyol data fetch failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            db.close()
    
    def _clear_trendyol_data(self, db: Session, start_dt: datetime, end_dt: datetime):
        """Mevcut Trendyol verilerini temizle"""
        logger.info(f"🗑️  Clearing existing Trendyol data ({start_dt.date()} to {end_dt.date()})")
        
        # Trendyol siparişlerini bul
        trendyol_orders = db.query(SalesOrder).filter(
            SalesOrder.marketplace.like('%Trendyol%'),
            SalesOrder.order_date >= start_dt,
            SalesOrder.order_date <= end_dt
        ).all()
        
        # İlgili item'ları sil
        for order in trendyol_orders:
            db.query(SalesOrderItem).filter(
                SalesOrderItem.order_id == order.id
            ).delete()
        
        # Siparişleri sil
        db.query(SalesOrder).filter(
            SalesOrder.marketplace.like('%Trendyol%'),
            SalesOrder.order_date >= start_dt,
            SalesOrder.order_date <= end_dt
        ).delete()
        
        db.commit()
        logger.info(f"   ✓ Cleared {len(trendyol_orders)} Trendyol orders")
    
    def _load_product_cache(self, db: Session):
        """Product cache'i yükle"""
        products = db.query(Product).all()
        
        for prod in products:
            # SKU ile cache
            if prod.sku:
                self.product_cache[prod.sku] = prod
            
            # Barcode ile cache
            if prod.barcode:
                self.product_cache[f"barcode_{prod.barcode}"] = prod
        
        logger.info(f"📦 Product cache loaded: {len(products)} products")
    
    def _process_and_store_trendyol_package(self, db: Session, package: Dict[str, Any]) -> int:
        """
        Bir Trendyol paketini işle ve database'e kaydet
        
        Returns:
            Number of items stored
        """
        # Sipariş bilgileri
        shipment_package_id = package.get('id')  # Trendyol shipmentPackageId
        order_number = package.get('orderNumber')  # Trendyol orderNumber
        
        # Sentos ID oluştur (Trendyol için negatif ID kullanıyoruz)
        # Bu şekilde Sentos ile çakışmaz
        sentos_order_id = -(shipment_package_id or 0)
        
        # Sipariş zaten var mı kontrol et
        existing = db.query(SalesOrder).filter(
            SalesOrder.trendyol_shipment_package_id == shipment_package_id
        ).first()
        
        if existing:
            logger.debug(f"   Order {shipment_package_id} already exists, skipping")
            return 0
        
        # Sipariş tarihi (Trendyol: milliseconds timestamp, GMT+3)
        order_date_ms = package.get('orderDate', 0)
        order_date = datetime.fromtimestamp(order_date_ms / 1000) if order_date_ms else datetime.now()
        
        # Sipariş statüsü map et
        status_str = package.get('status', 'Created')
        order_status = self._map_trendyol_status(status_str)
        
        # Sipariş kaydet
        order = SalesOrder(
            sentos_order_id=sentos_order_id,
            order_code=package.get('cargoTrackingNumber', order_number),
            trendyol_shipment_package_id=shipment_package_id,
            trendyol_order_number=order_number,
            order_date=order_date,
            marketplace='Trendyol',
            shop='Trendyol',
            order_status=order_status,
            order_total=package.get('grossAmount', 0.0),
            shipping_total=0.0,  # Trendyol'da shipping ayrı gelmiyor
            carrying_charge=0.0,
            service_fee=0.0,
            cargo_provider=package.get('cargoProviderName', ''),
            cargo_number=package.get('cargoTrackingNumber', ''),
            has_invoice='yes' if package.get('invoiceLink') else 'no',
            invoice_type='',
            invoice_number=''
        )
        
        db.add(order)
        db.flush()  # ID al
        
        # Order items
        lines = package.get('lines', [])
        items_count = 0
        
        for line in lines:
            try:
                item = self._create_trendyol_order_item(db, order, line)
                if item:
                    db.add(item)
                    items_count += 1
            except Exception as e:
                logger.error(f"❌ Error creating item for line {line.get('id')}: {e}")
                logger.error(f"   Line data: {line}")
                continue
        
        return items_count
    
    def _create_trendyol_order_item(
        self, 
        db: Session, 
        order: SalesOrder, 
        line: Dict[str, Any]
    ) -> Optional[SalesOrderItem]:
        """Trendyol order line'ı SalesOrderItem'a çevir"""
        
        order_line_id = line.get('id')  # Trendyol orderLineId
        quantity = line.get('quantity', 1)
        merchant_sku = line.get('merchantSku', '')
        barcode = line.get('barcode', '')
        
        # Product bilgilerini bul
        product = self._find_product(merchant_sku, barcode)
        
        # Maliyet hesapla
        unit_cost = 0.0
        if product and product.cost:
            unit_cost = product.cost
        
        # Unique key
        unique_key = f"trendyol_{order.trendyol_shipment_package_id}_{order_line_id}"
        
        # İtem statüsü
        item_status_name = line.get('orderLineItemStatusName', '')
        is_return = 'return' in item_status_name.lower() or 'iade' in item_status_name.lower()
        
        # Fiyat bilgileri (None kontrolü!)
        unit_price = line.get('price') or 0.0
        discount = line.get('discount') or 0.0
        amount = line.get('amount') or (unit_price * quantity)
        
        # Commission (None-safe)
        commission_amount = line.get('commission') or 0.0
        commission_rate = (commission_amount / amount * 100) if (amount and amount > 0) else 0.0
        
        item = SalesOrderItem(
            order_id=order.id,
            sentos_order_id=order.sentos_order_id,
            sentos_item_id=0,  # Trendyol için yok
            trendyol_order_line_id=order_line_id,
            unique_key=unique_key,
            product_name=line.get('productName', ''),
            product_sku=merchant_sku,
            barcode=barcode,
            color=line.get('productColor', ''),
            model_name='',
            model_value=line.get('productSize', ''),
            item_status='rejected' if is_return else 'accepted',
            quantity=quantity,
            unit_price=unit_price,
            item_amount=amount,
            unit_cost_with_vat=unit_cost,
            total_cost_with_vat=unit_cost * quantity,
            commission_rate=commission_rate,
            commission_amount=commission_amount,
            is_return=is_return,
            is_cancelled=(order.order_status == OrderStatus.IPTAL_IADE.value)
        )
        
        return item
    
    def _find_product(self, sku: str, barcode: str) -> Optional[Product]:
        """Product cache'den ürün bul"""
        # Önce SKU ile
        if sku and sku in self.product_cache:
            return self.product_cache[sku]
        
        # Barcode ile
        if barcode:
            key = f"barcode_{barcode}"
            if key in self.product_cache:
                return self.product_cache[key]
        
        return None
    
    def _map_trendyol_status(self, status: str) -> int:
        """
        Trendyol status'ü Sentos status'e map et
        
        Trendyol: Created, Picking, Invoiced, Shipped, Delivered, Cancelled, etc.
        Sentos: 1-6, 99
        """
        status_map = {
            'Awaiting': OrderStatus.ONAY_BEKLIYOR.value,  # 1
            'Created': OrderStatus.ONAY_BEKLIYOR.value,   # 1 (gönderime hazır)
            'Picking': OrderStatus.ONAYLANDI.value,       # 2 (toplanıyor)
            'Invoiced': OrderStatus.ONAYLANDI.value,      # 2 (faturalandı)
            'Shipped': OrderStatus.KARGOYA_VERILDI.value, # 5
            'Delivered': OrderStatus.TESLIM_EDILDI.value, # 99
            'Cancelled': OrderStatus.IPTAL_IADE.value,    # 6
            'UnSupplied': OrderStatus.IPTAL_IADE.value,   # 6
            'UnDelivered': OrderStatus.IPTAL_IADE.value,  # 6
            'Returned': OrderStatus.IPTAL_IADE.value,     # 6
            'UnPacked': OrderStatus.ONAYLANDI.value,      # 2 (bölünmüş)
            'AtCollectionPoint': OrderStatus.KARGOYA_VERILDI.value  # 5
        }
        
        return status_map.get(status, OrderStatus.ONAY_BEKLIYOR.value)
