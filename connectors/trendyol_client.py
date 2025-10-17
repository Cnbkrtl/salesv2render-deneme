"""
Trendyol Marketplace API Client
Trendyol API ile entegrasyon için client sınıfı
"""
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TrendyolAPIClient:
    """
    Trendyol Marketplace API entegrasyonu
    
    API Dokümantasyonu:
    https://developers.trendyol.com/docs/marketplace/siparis-entegrasyonu/siparis-paketlerini-cekme
    
    Endpoint: GET /integration/order/sellers/{sellerId}/orders
    
    Auth: Basic Authentication
    - Username: API Key (Supplier ID)
    - Password: API Secret
    """
    
    def __init__(
        self,
        api_url: str = "https://apigw.trendyol.com",
        supplier_id: str = None,
        api_key: str = None,
        api_secret: str = None,
        timeout: int = 30
    ):
        """
        Args:
            api_url: Base URL (prod: apigw.trendyol.com, stage: stageapigw.trendyol.com)
            supplier_id: Trendyol Supplier/Seller ID
            api_key: API Key (tedarikçi numarası)
            api_secret: API Secret
            timeout: İstek timeout süresi (saniye)
        """
        self.api_url = api_url.rstrip('/')
        self.supplier_id = supplier_id
        self.api_key = api_key  # API Key (authentication için gerekli)
        self.api_secret = api_secret
        self.timeout = timeout
        self.session = requests.Session()
        
        # Basic Auth - API Key kullanılmalı (Supplier ID değil!)
        if self.api_key and self.api_secret:
            self.session.auth = (self.api_key, self.api_secret)
        elif self.api_secret:
            # Fallback: Sadece API secret varsa hata ver
            raise ValueError("TRENDYOL_API_KEY gerekli! (Supplier ID ile aynı değil)")
        
        # Headers
        self.session.headers.update({
            'User-Agent': 'SalesAnalytics/2.0',
            'Content-Type': 'application/json'
        })
        
        logger.info(f"TrendyolAPIClient initialized: {self.api_url}")
        if self.supplier_id:
            logger.info(f"  Supplier ID: {self.supplier_id}")
    
    def get_shipment_packages(
        self,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 0,
        size: int = 200,
        order_by_field: str = "PackageLastModifiedDate",
        order_by_direction: str = "DESC"
    ) -> Dict[str, Any]:
        """
        Sipariş paketlerini çek (getShipmentPackages)
        
        Args:
            status: Sipariş statüsü (Created, Picking, Invoiced, Shipped, Cancelled, 
                    Delivered, UnDelivered, Returned, UnPacked, UnSupplied, AtCollectionPoint)
            start_date: Başlangıç tarihi (GMT+3, timestamp milliseconds)
            end_date: Bitiş tarihi (GMT+3, timestamp milliseconds)
            page: Sayfa numarası (0-based)
            size: Sayfa boyutu (max 200)
            order_by_field: Sıralama alanı (PackageLastModifiedDate önerilir)
            order_by_direction: Sıralama yönü (ASC/DESC)
        
        Returns:
            {
                'page': 0,
                'size': 200,
                'totalPages': 5,
                'totalElements': 1000,
                'content': [...]  # Sipariş paketleri
            }
        """
        if not self.supplier_id:
            raise ValueError("Supplier ID gerekli")
        
        # Endpoint
        endpoint = f"/integration/order/sellers/{self.supplier_id}/orders"
        url = f"{self.api_url}{endpoint}"
        
        # Parametreler
        params = {
            'page': page,
            'size': min(size, 200),  # Max 200
            'orderByField': order_by_field,
            'orderByDirection': order_by_direction
        }
        
        # Status filtresi
        if status:
            params['status'] = status
        
        # Tarih filtreleri (GMT+3 timezone, milliseconds)
        if start_date:
            params['startDate'] = int(start_date.timestamp() * 1000)
        if end_date:
            params['endDate'] = int(end_date.timestamp() * 1000)
        
        # İstek at
        try:
            logger.info(f"📦 Fetching Trendyol orders: status={status}, page={page}, size={size}")
            logger.debug(f"   URL: {url}")
            logger.debug(f"   Params: {params}")
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Bilgilendirme log
            total_elements = data.get('totalElements', 0)
            total_pages = data.get('totalPages', 0)
            content_count = len(data.get('content', []))
            
            logger.info(f"✅ Fetched {content_count} packages (page {page+1}/{total_pages}, total: {total_elements})")
            
            return data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP Error: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.Timeout:
            logger.error(f"❌ Request timeout ({self.timeout}s)")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            raise
    
    def get_all_shipment_packages(
        self,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Tüm sipariş paketlerini çek (pagination ile)
        
        Args:
            status: Sipariş statüsü
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            max_pages: Maksimum sayfa sayısı (None = tümü)
        
        Returns:
            List of order packages
        """
        all_packages = []
        page = 0
        
        while True:
            # Maksimum sayfa kontrolü
            if max_pages is not None and page >= max_pages:
                logger.info(f"⚠️ Reached max_pages limit ({max_pages})")
                break
            
            # Sayfa çek
            result = self.get_shipment_packages(
                status=status,
                start_date=start_date,
                end_date=end_date,
                page=page,
                size=200
            )
            
            # İçeriği ekle
            content = result.get('content', [])
            if not content:
                logger.info(f"📭 No more packages (page {page})")
                break
            
            all_packages.extend(content)
            
            # Son sayfa mı?
            total_pages = result.get('totalPages', 0)
            if page >= total_pages - 1:
                logger.info(f"✅ Reached last page ({page + 1}/{total_pages})")
                break
            
            page += 1
        
        logger.info(f"🎉 Total packages fetched: {len(all_packages)}")
        return all_packages
    
    def get_orders_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        statuses: Optional[List[str]] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Belirli tarih aralığındaki tüm siparişleri çek
        
        Args:
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            statuses: Sipariş statüleri listesi (None = tümü)
            max_pages: Maksimum sayfa sayısı
        
        Returns:
            List of order packages
        """
        # Tüm statüler (varsayılan)
        if statuses is None:
            statuses = [
                'Created',           # Gönderime hazır
                'Picking',           # Toplanıyor
                'Invoiced',          # Faturalandı
                'Shipped',           # Kargoya verildi
                'Delivered',         # Teslim edildi
                'Cancelled',         # İptal edildi
                'UnSupplied',        # Tedarik edilemedi (iptal alt kategorisi)
                'UnDelivered',       # Teslim edilemedi
                'Returned',          # İade edildi (müşteriye ulaşmayan ve geri dönen)
                'UnPacked',          # Bölünmüş paketler (kısmi iptal sonrası yeni paket)
                'AtCollectionPoint'  # PUDO teslimat noktasında
            ]
        
        all_orders = []
        
        for status in statuses:
            logger.info(f"🔍 Fetching orders with status={status}")
            
            orders = self.get_all_shipment_packages(
                status=status,
                start_date=start_date,
                end_date=end_date,
                max_pages=max_pages
            )
            
            all_orders.extend(orders)
            logger.info(f"   ✓ Found {len(orders)} orders for status={status}")
        
        # Tekrar edenleri temizle (shipmentPackageId'ye göre)
        unique_orders = {}
        for order in all_orders:
            package_id = order.get('id')  # shipmentPackageId
            if package_id and package_id not in unique_orders:
                unique_orders[package_id] = order
        
        result = list(unique_orders.values())
        logger.info(f"🎯 Total unique orders: {len(result)} (from {len(all_orders)} total)")
        
        return result
    
    def get_product_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        page: int = 0,
        size: int = 50
    ) -> Dict[str, Any]:
        """
        Ürün istatistiklerini çek (getProductStatistics)
        
        Endpoint: GET /integration/product/sellers/{sellerId}/statistics
        
        Args:
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            page: Sayfa numarası (0-based)
            size: Sayfa boyutu (max 50)
        
        Returns:
            {
                'page': 0,
                'size': 50,
                'totalPages': 10,
                'totalElements': 500,
                'content': [
                    {
                        'barcode': '1234567890123',
                        'productCode': 'SKU123',
                        'productName': 'Ürün Adı',
                        'brand': 'Marka',
                        'categoryName': 'Kategori',
                        'price': 100.0,
                        'discountedPrice': 80.0,
                        'stock': 10,
                        'orderCount': 50,      # Sipariş sayısı
                        'soldQuantity': 75,     # Satılan adet
                        'revenue': 4000.0,      # Ciro
                        'favoriteCount': 20,    # Favoriye eklenme
                        'visitCount': 500       # Görüntülenme
                    },
                    ...
                ]
            }
        """
        if not self.supplier_id:
            raise ValueError("Supplier ID gerekli")
        
        # Tarih formatı: milliseconds timestamp (GMT+3)
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        endpoint = f"/integration/product/sellers/{self.supplier_id}/statistics"
        
        params = {
            'startDate': start_ts,
            'endDate': end_ts,
            'page': page,
            'size': min(size, 50),  # Max 50
        }
        
        try:
            response = self.session.get(
                f"{self.api_url}{endpoint}",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(
                f"✅ Product stats fetched: page={data.get('page', 0)}, "
                f"total={data.get('totalElements', 0)}"
            )
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Product statistics request failed: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"   Response: {e.response.text}")
            raise
    
    def get_all_product_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Tüm ürün istatistiklerini çek (pagination)
        
        Args:
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            max_pages: Maksimum sayfa sayısı (None=tümü)
        
        Returns:
            Ürün istatistikleri listesi
        """
        all_products = []
        page = 0
        
        logger.info(f"📊 Fetching all Trendyol product statistics...")
        logger.info(f"   Date range: {start_date.date()} - {end_date.date()}")
        
        while True:
            if max_pages and page >= max_pages:
                logger.info(f"⚠️ Reached max_pages limit: {max_pages}")
                break
            
            result = self.get_product_statistics(
                start_date=start_date,
                end_date=end_date,
                page=page,
                size=50
            )
            
            products = result.get('content', [])
            if not products:
                break
            
            all_products.extend(products)
            
            total_pages = result.get('totalPages', 0)
            logger.info(f"   Page {page + 1}/{total_pages}: {len(products)} products")
            
            # Son sayfa kontrolü
            if page >= total_pages - 1:
                break
            
            page += 1
        
        logger.info(f"✅ Total products fetched: {len(all_products)}")
        return all_products


def create_trendyol_client_from_config(config) -> TrendyolAPIClient:
    """
    Config'den Trendyol client oluştur
    
    Args:
        config: Settings objesi (from app.core.config)
    
    Returns:
        TrendyolAPIClient instance
    """
    return TrendyolAPIClient(
        api_url=getattr(config, 'trendyol_api_url', 'https://apigw.trendyol.com'),
        supplier_id=getattr(config, 'trendyol_supplier_id', None),
        api_key=getattr(config, 'trendyol_api_key', None),
        api_secret=getattr(config, 'trendyol_api_secret', None),
        timeout=30
    )
