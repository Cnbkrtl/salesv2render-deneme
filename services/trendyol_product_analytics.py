"""
Trendyol Product Analytics Service
Trendyol ürün performans verilerini Sentos ile birleştir
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from connectors.trendyol_client import TrendyolAPIClient
from database.models import Product

logger = logging.getLogger(__name__)


class TrendyolProductAnalyticsService:
    """
    Trendyol'a özgü ürün analitiği servisi
    
    Trendyol API'den ürün performans istatistiklerini çeker ve
    Sentos'tan gelen verilerle birleştirir.
    """
    
    def __init__(self, trendyol_client: TrendyolAPIClient):
        """
        Args:
            trendyol_client: TrendyolAPIClient instance
        """
        self.client = trendyol_client
    
    def fetch_trendyol_product_stats(
        self,
        start_date: datetime,
        end_date: datetime,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Trendyol ürün istatistiklerini çek
        
        Args:
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            max_pages: Maksimum sayfa sayısı
        
        Returns:
            Ürün istatistikleri listesi
        """
        logger.info("📊 Fetching Trendyol product statistics...")
        
        stats = self.client.get_all_product_statistics(
            start_date=start_date,
            end_date=end_date,
            max_pages=max_pages
        )
        
        logger.info(f"✅ Fetched {len(stats)} Trendyol product stats")
        return stats
    
    def combine_with_sentos_data(
        self,
        db: Session,
        trendyol_stats: List[Dict[str, Any]],
        sentos_product_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Trendyol istatistiklerini Sentos verileriyle birleştir
        
        Args:
            db: Database session
            trendyol_stats: Trendyol'dan gelen ürün istatistikleri
            sentos_product_data: Sentos'tan gelen ürün performans verileri
        
        Returns:
            Birleştirilmiş ürün performans verileri
        """
        logger.info("🔄 Combining Trendyol and Sentos product data...")
        
        # Trendyol verilerini barcode'a göre indexle
        trendyol_by_barcode = {}
        for stat in trendyol_stats:
            barcode = stat.get('barcode')
            if barcode:
                trendyol_by_barcode[barcode] = {
                    'marketplace': 'Trendyol',
                    'barcode': barcode,
                    'product_code': stat.get('productCode'),
                    'product_name': stat.get('productName'),
                    'brand': stat.get('brand'),
                    'category': stat.get('categoryName'),
                    'price': stat.get('price', 0),
                    'discounted_price': stat.get('discountedPrice', 0),
                    'stock': stat.get('stock', 0),
                    'order_count': stat.get('orderCount', 0),
                    'sold_quantity': stat.get('soldQuantity', 0),
                    'revenue': stat.get('revenue', 0),
                    'favorite_count': stat.get('favoriteCount', 0),
                    'visit_count': stat.get('visitCount', 0),
                    'source': 'trendyol_api'  # Kaynak belirt
                }
        
        # Sentos verilerini barcode'a göre indexle
        sentos_by_barcode = {}
        for product in sentos_product_data:
            barcode = product.get('barcode')
            if barcode:
                sentos_by_barcode[barcode] = {
                    **product,
                    'source': 'sentos_orders'  # Kaynak belirt
                }
        
        # Birleştir
        combined = []
        
        # Önce Trendyol verilerini ekle
        for barcode, trendyol_data in trendyol_by_barcode.items():
            sentos_data = sentos_by_barcode.get(barcode, {})
            
            # Database'den ürün bilgisini al (maliyet için)
            product = db.query(Product).filter(Product.barcode == barcode).first()
            
            combined_item = {
                **trendyol_data,
                # Sentos'tan gelen verilerle tamamla
                'sentos_order_count': sentos_data.get('order_count', 0),
                'sentos_revenue': sentos_data.get('revenue', 0),
                'sentos_sold_quantity': sentos_data.get('sold_quantity', 0),
                # Database'den maliyet
                'cost': product.cost_with_vat if product and product.cost_with_vat else 0,
                # Toplam değerler (Trendyol + Sentos)
                'total_order_count': trendyol_data.get('order_count', 0) + sentos_data.get('order_count', 0),
                'total_revenue': trendyol_data.get('revenue', 0) + sentos_data.get('revenue', 0),
                'total_sold_quantity': trendyol_data.get('sold_quantity', 0) + sentos_data.get('sold_quantity', 0),
            }
            
            # Karlılık hesapla
            total_revenue = combined_item['total_revenue']
            total_cost = combined_item['cost'] * combined_item['total_sold_quantity']
            combined_item['profit'] = total_revenue - total_cost
            combined_item['profit_margin'] = (
                (combined_item['profit'] / total_revenue * 100) if total_revenue > 0 else 0
            )
            
            combined.append(combined_item)
        
        # Sentos'ta olup Trendyol'da olmayan ürünleri ekle
        for barcode, sentos_data in sentos_by_barcode.items():
            if barcode not in trendyol_by_barcode:
                product = db.query(Product).filter(Product.barcode == barcode).first()
                
                combined_item = {
                    'marketplace': sentos_data.get('marketplace', 'Unknown'),
                    'barcode': barcode,
                    'product_code': sentos_data.get('product_code', ''),
                    'product_name': sentos_data.get('product_name', ''),
                    'brand': '',
                    'category': '',
                    'price': 0,
                    'discounted_price': 0,
                    'stock': 0,
                    'order_count': 0,
                    'sold_quantity': 0,
                    'revenue': 0,
                    'favorite_count': 0,
                    'visit_count': 0,
                    'source': 'sentos_only',
                    'sentos_order_count': sentos_data.get('order_count', 0),
                    'sentos_revenue': sentos_data.get('revenue', 0),
                    'sentos_sold_quantity': sentos_data.get('sold_quantity', 0),
                    'cost': product.cost_with_vat if product and product.cost_with_vat else 0,
                    'total_order_count': sentos_data.get('order_count', 0),
                    'total_revenue': sentos_data.get('revenue', 0),
                    'total_sold_quantity': sentos_data.get('sold_quantity', 0),
                }
                
                # Karlılık hesapla
                total_revenue = combined_item['total_revenue']
                total_cost = combined_item['cost'] * combined_item['total_sold_quantity']
                combined_item['profit'] = total_revenue - total_cost
                combined_item['profit_margin'] = (
                    (combined_item['profit'] / total_revenue * 100) if total_revenue > 0 else 0
                )
                
                combined.append(combined_item)
        
        logger.info(f"✅ Combined {len(combined)} products")
        logger.info(f"   - Trendyol only: {len(trendyol_by_barcode)}")
        logger.info(f"   - Sentos only: {len(sentos_by_barcode) - len(set(trendyol_by_barcode.keys()) & set(sentos_by_barcode.keys()))}")
        logger.info(f"   - Both: {len(set(trendyol_by_barcode.keys()) & set(sentos_by_barcode.keys()))}")
        
        return combined
    
    def get_top_products(
        self,
        combined_data: List[Dict[str, Any]],
        sort_by: str = 'total_revenue',
        limit: int = 10,
        marketplace_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Top N ürünleri getir
        
        Args:
            combined_data: Birleştirilmiş ürün verileri
            sort_by: Sıralama kriteri (total_revenue, profit, total_sold_quantity, etc.)
            limit: Kaç ürün gösterilecek (10, 20, 50, etc.)
            marketplace_filter: Marketplace filtresi (None=tümü, 'Trendyol', etc.)
        
        Returns:
            Top N ürün listesi
        """
        # Marketplace filtresi uygula
        filtered = combined_data
        if marketplace_filter:
            filtered = [p for p in combined_data if p.get('marketplace') == marketplace_filter]
        
        # Sırala ve limitle
        sorted_products = sorted(
            filtered,
            key=lambda x: x.get(sort_by, 0),
            reverse=True
        )
        
        return sorted_products[:limit]
    
    def get_marketplace_breakdown(
        self,
        combined_data: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Marketplace bazında dağılım
        
        Returns:
            {
                'Trendyol': {
                    'product_count': 100,
                    'total_revenue': 50000,
                    'total_sold_quantity': 500,
                    'total_profit': 10000
                },
                'LCW': {...},
                ...
            }
        """
        breakdown = {}
        
        for product in combined_data:
            marketplace = product.get('marketplace', 'Unknown')
            
            if marketplace not in breakdown:
                breakdown[marketplace] = {
                    'product_count': 0,
                    'total_revenue': 0,
                    'total_sold_quantity': 0,
                    'total_profit': 0,
                    'avg_profit_margin': 0
                }
            
            breakdown[marketplace]['product_count'] += 1
            breakdown[marketplace]['total_revenue'] += product.get('total_revenue', 0)
            breakdown[marketplace]['total_sold_quantity'] += product.get('total_sold_quantity', 0)
            breakdown[marketplace]['total_profit'] += product.get('profit', 0)
        
        # Average profit margin hesapla
        for marketplace, data in breakdown.items():
            if data['total_revenue'] > 0:
                data['avg_profit_margin'] = (data['total_profit'] / data['total_revenue']) * 100
        
        return breakdown
