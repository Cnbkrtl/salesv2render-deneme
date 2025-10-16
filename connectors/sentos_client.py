"""
Sentos API Connector v2 - Optimize ve Doğru Field Mapping
"""
import requests
import time
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class SentosAPIClient:
    """Sentos API Client - Orders ve Products endpoint'leri"""
    
    def __init__(self, api_url: str, api_key: str, api_secret: str, api_cookie: str = None):
        self.api_url = api_url.strip().rstrip('/')
        self.auth = HTTPBasicAuth(api_key, api_secret)
        self.api_cookie = api_cookie
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Cookie varsa header'a ekle
        if api_cookie:
            self.headers["Cookie"] = api_cookie
            logger.info("🍪 Cookie added to request headers")
        
        # Retry settings - Rate limiting için optimize edildi
        self.max_retries = 5
        self.retry_delay = 5  # İlk retry 5 saniye
        self.rate_limit_delay = 1.0  # İstekler arası minimum bekleme
        
        logger.info(f"SentosAPIClient initialized: {self.api_url}")
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Dict = None, 
        data: Dict = None,
        timeout: int = 60
    ) -> requests.Response:
        """HTTP request with retry logic"""
        url = urljoin(self.api_url + '/', endpoint.lstrip('/'))
        
        # Rate limiting - her istekten önce bekle
        time.sleep(self.rate_limit_delay)
        
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    auth=self.auth,
                    params=params,
                    json=data,
                    timeout=timeout
                )
                response.raise_for_status()
                return response
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in [429, 500, 502, 503, 504] and attempt < self.max_retries - 1:
                    # 429: Rate limit, 5xx: Server errors
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"HTTP {e.response.status_code}, retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API Error ({url}): {e}")
                    raise
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Connection Error ({url}): {e}")
                raise
    
    # ========================================================================
    # ORDERS API - DÜZELTILMIŞ VE OPTIMIZE EDİLMİŞ
    # ========================================================================
    
    def get_orders(
        self,
        start_date: str = None,
        end_date: str = None,
        marketplace: str = None,
        status: int = None,
        page: int = 1,
        size: int = 100
    ) -> Dict[str, Any]:
        """
        Siparişleri çeker (paginated)
        
        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD)
            end_date: Bitiş tarihi (YYYY-MM-DD)
            marketplace: Marketplace filtresi
            status: Status filtresi (1,2,3,4,5,6,99)
            page: Sayfa numarası
            size: Sayfa başına kayıt
            
        Returns:
            {
                'orders': List[Dict],
                'total': int,
                'page': int,
                'total_pages': int
            }
        """
        params = {
            'page': page,
            'size': size
        }
        
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if marketplace:
            params['marketplace'] = marketplace.upper()
        if status is not None:
            params['status'] = status
        
        logger.info(f"Fetching orders: page={page}, filters={params}")
        
        try:
            response = self._make_request("GET", "/orders", params=params)
            data = response.json()
            
            # Response parsing - farklı API formatlarına uyum
            if isinstance(data, dict):
                orders = data.get('data', data.get('content', data.get('orders', [])))
                total = data.get('total', data.get('totalElements', len(orders)))
                total_pages = data.get('totalPages', data.get('total_pages', 1))
            elif isinstance(data, list):
                orders = data
                total = len(orders)
                total_pages = 1
            else:
                orders = []
                total = 0
                total_pages = 1
            
            logger.info(f"Fetched {len(orders)} orders (page {page}/{total_pages})")
            
            return {
                'orders': orders,
                'total': total,
                'page': page,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            raise
    
    def get_order_detail(self, order_id: int) -> Optional[Dict]:
        """Tek sipariş detayı çeker"""
        try:
            response = self._make_request("GET", f"/orders/{order_id}")
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching order {order_id}: {e}")
            return None
    
    def get_all_orders(
        self,
        start_date: str = None,
        end_date: str = None,
        marketplace: str = None,
        status: int = None,
        page_size: int = 100,
        max_pages: int = None,
        progress_callback: callable = None  # YENİ: Progress tracking
    ) -> List[Dict]:
        """
        Tüm siparişleri pagination ile çeker
        
        Args:
            max_pages: Maksimum sayfa sayısı (None = tümü)
            progress_callback: Progress callback function(fetched, total, page, total_pages)
            
        Returns:
            List of all orders
        """
        all_orders = []
        page = 1
        total_pages_info = None
        
        while True:
            if max_pages and page > max_pages:
                break
                
            result = self.get_orders(
                start_date=start_date,
                end_date=end_date,
                marketplace=marketplace,
                status=status,
                page=page,
                size=page_size
            )
            
            orders = result.get('orders', [])
            if not orders:
                break
            
            all_orders.extend(orders)
            
            # Progress callback
            if progress_callback and not total_pages_info:
                total_pages_info = result.get('total_pages', 1)
            
            if progress_callback:
                progress_callback({
                    'fetched': len(all_orders),
                    'total': result.get('total', len(all_orders)),
                    'page': page,
                    'total_pages': total_pages_info or page
                })
            
            # Son sayfa kontrolü
            if page >= result.get('total_pages', 1):
                break
            
            page += 1
            time.sleep(self.rate_limit_delay)  # Rate limiting - daha uzun bekleme
        
        logger.info(f"Fetched total {len(all_orders)} orders")
        return all_orders
    
    # ========================================================================
    # PRODUCTS API - MALİYET ÇEKME İÇİN
    # ========================================================================
    
    def get_product(self, product_id: int) -> Optional[Dict]:
        """
        Ürün detayını çeker (maliyet bilgisi için)
        
        Returns:
            {
                'id': int,
                'sku': str,
                'name': str,
                'purchase_price': float,  # <-- MALİYET (KDV'siz)
                'sale_price': float,
                'vat_rate': int,          # <-- KDV oranı
                'variants': []
            }
        """
        try:
            response = self._make_request("GET", f"/products/{product_id}")
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {e}")
            return None
    
    def get_product_by_sku(self, sku: str, barcode: str = None) -> Optional[Dict]:
        """
        SKU veya barcode ile ürün arar
        Alış fiyatı arama parametreleri gibi çoklu parametrelerle arama yapar:
        1. Önce doğrudan SKU ile ara
        2. Bulamazsa barcode ile ara
        3. Bulamazsa normalize edilmiş SKU varyantları ile ara (S prefix, leading zeros)
        
        Sentos API Response: { page, size, total_elements, total_pages, data: [...] }
        """
        try:
            # 1. Önce SKU ile ara
            params = {'sku': sku, 'size': 1}
            response = self._make_request("GET", "/products", params=params)
            data = response.json()
            
            # Sentos API response: { "data": [...] }
            products = data.get('data', [])
            
            # SKU ile bulunamadıysa ve barcode varsa, barcode ile ara
            if not products and barcode:
                logger.info(f"SKU {sku} not found, trying barcode: {barcode}")
                params = {'barcode': barcode, 'size': 1}
                response = self._make_request("GET", "/products", params=params)
                data = response.json()
                products = data.get('data', [])
            
            # Hala bulunamadıysa, normalize edilmiş SKU varyantları ile dene
            if not products:
                sku_variants = self._normalize_sku_variants(sku)
                for variant in sku_variants:
                    if variant != sku:
                        logger.info(f"SKU {sku} not found, trying normalized variant: {variant}")
                        params = {'sku': variant, 'size': 1}
                        response = self._make_request("GET", "/products", params=params)
                        data = response.json()
                        products = data.get('data', [])
                        if products:
                            logger.info(f"✅ Found with normalized SKU: {variant}")
                            break
            
            if not products:
                return None
            
            product = products[0]
            
            # Eğer ana üründe image yoksa, variants'tan ilk görseli al
            if (not product.get('images') or len(product.get('images', [])) == 0):
                variants = product.get('variants', [])
                if variants and len(variants) > 0:
                    first_variant = variants[0]
                    variant_images = first_variant.get('images', [])
                    if variant_images:
                        # Variant'taki görselleri ana ürüne kopyala
                        product['images'] = variant_images
                        logger.info(f"Image from variant: {sku} -> {len(variant_images)} images")
            
            return product
            
        except Exception as e:
            logger.error(f"Error fetching product by SKU {sku}: {e}")
            return None
    
    def _normalize_sku_variants(self, sku: str) -> List[str]:
        """
        SKU normalizasyon varyantları üretir (alış fiyatı arama gibi)
        
        Örnekler:
        - "S0123" -> ["S0123", "0123", "123"]
        - "00123" -> ["00123", "0123", "123"]
        - "123" -> ["123", "S123", "S0123", "00123"]
        """
        if not sku:
            return []
        
        variants = [sku]  # Orijinali her zaman ekle
        
        # S prefix'i varsa kaldır
        if sku.startswith('S'):
            no_s = sku[1:]
            variants.append(no_s)
            # Leading zero'ları da kaldır
            variants.append(no_s.lstrip('0') or '0')
        
        # Leading zero varsa kaldır
        if sku[0] == '0':
            variants.append(sku.lstrip('0') or '0')
        
        # Sayısal SKU ise, S ekle ve leading zero ekle
        if sku.isdigit():
            variants.append(f"S{sku}")
            variants.append(f"S{sku.zfill(5)}")  # S00123 formatı
            variants.append(sku.zfill(5))  # 00123 formatı
        
        # Tekrar edenleri temizle, sıralamayı koru
        seen = set()
        unique_variants = []
        for v in variants:
            if v not in seen:
                seen.add(v)
                unique_variants.append(v)
        
        return unique_variants
    
    def get_products_bulk(self, page: int = 1, size: int = 100) -> Dict[str, Any]:
        """
        Ürünleri toplu çeker (maliyet cache için)
        
        Sentos API Response Format:
        {
            "page": 1,
            "size": 100,
            "total_elements": 1234,
            "total_pages": 13,
            "data": [...]
        }
        
        Returns:
            {
                'products': List[Dict],
                'total': int,
                'page': int,
                'total_pages': int
            }
        """
        try:
            params = {'page': page, 'size': size}
            response = self._make_request("GET", "/products", params=params)
            data = response.json()
            
            # Sentos API response formatı: { page, size, total_elements, total_pages, data }
            products = data.get('data', [])
            total = data.get('total_elements', len(products))
            total_pages = data.get('total_pages', 1)
            current_page = data.get('page', page)
            
            logger.info(f"📊 Page {current_page}/{total_pages} - {len(products)} products (Total: {total})")
            
            # Her ürün için: image yoksa variants'tan al
            for product in products:
                if (not product.get('images') or len(product.get('images', [])) == 0):
                    variants = product.get('variants', [])
                    if variants and len(variants) > 0:
                        first_variant = variants[0]
                        variant_images = first_variant.get('images', [])
                        if variant_images:
                            product['images'] = variant_images
            
            return {
                'products': products,
                'total': total,
                'page': current_page,
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            raise
    
    # ========================================================================
    # PLATFORMS API - RETAIL FİLTRELEME İÇİN
    # ========================================================================
    
    def get_platforms(self) -> Dict[str, List[Dict]]:
        """
        Aktif platformları çeker
        
        Returns:
            {
                'trendyol': [{'id': 1, 'name': 'Store1'}],
                'shopify': [...],
                ...
            }
        """
        try:
            response = self._make_request("GET", "/platforms")
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching platforms: {e}")
            return {}
    
    # ========================================================================
    # HEALTH CHECK
    # ========================================================================
    
    def test_connection(self) -> Dict[str, Any]:
        """API bağlantısını test eder"""
        try:
            response = self._make_request("GET", "/orders", params={'page': 1, 'size': 1})
            return {
                'success': True,
                'message': 'Sentos API connection successful',
                'status_code': response.status_code
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Sentos API connection failed: {str(e)}'
            }
