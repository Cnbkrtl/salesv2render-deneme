"""
Product Performance Service
Ürün performans analizi - detaylı metrikler
"""
import logging
from sqlalchemy import func, and_, or_, case
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import sys
import os

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_db
from database.models import SalesOrder, SalesOrderItem, Product
from services.data_fetcher import extract_base_sku


class ProductPerformanceService:
    """Ürün performans analizi servisi"""
    
    def __init__(self):
        self.db = next(get_db())
        self._image_cache = {}  # SKU -> image_url cache
    
    def analyze_performance(
        self,
        start_date: datetime,
        end_date: datetime,
        marketplace: Optional[str] = None,
        top_n: int = 20,
        sort_by: str = "revenue"
    ) -> Dict[str, Any]:
        """
        Ürün performans analizi
        
        Returns:
            {
                "top_performers": [...],
                "worst_performers": [...],
                "total_products": int,
                "date_range": {...},
                "marketplace": str,
                "total_revenue": float,
                "total_profit": float,
                "avg_profit_margin": float
            }
        """
        
        # Base query - JOIN orders + items
        base_query = self.db.query(
            SalesOrderItem.product_sku,
            SalesOrderItem.product_name,
            SalesOrderItem.barcode,
            SalesOrderItem.model_name,
            
            # Sales metrics
            func.sum(
                case(
                    (and_(SalesOrderItem.is_return == False, SalesOrderItem.is_cancelled == False), 
                     SalesOrderItem.item_amount),
                    else_=0
                )
            ).label('total_revenue'),
            
            func.sum(
                case(
                    (and_(SalesOrderItem.is_return == False, SalesOrderItem.is_cancelled == False), 
                     SalesOrderItem.quantity),
                    else_=0
                )
            ).label('total_quantity'),
            
            func.count(
                func.distinct(
                    case(
                        (and_(SalesOrderItem.is_return == False, SalesOrderItem.is_cancelled == False), 
                         SalesOrderItem.order_id),
                        else_=None
                    )
                )
            ).label('total_orders'),
            
            # Cost
            func.sum(
                case(
                    (and_(SalesOrderItem.is_return == False, SalesOrderItem.is_cancelled == False), 
                     SalesOrderItem.total_cost_with_vat),
                    else_=0
                )
            ).label('total_cost'),
            
            # Returns
            func.sum(
                case(
                    (SalesOrderItem.is_return == True, SalesOrderItem.quantity),
                    else_=0
                )
            ).label('return_quantity'),
            
            func.sum(
                case(
                    (SalesOrderItem.is_return == True, SalesOrderItem.item_amount),
                    else_=0
                )
            ).label('return_revenue_loss'),
            
        ).join(
            SalesOrder,
            SalesOrderItem.order_id == SalesOrder.id
        ).filter(
            func.date(SalesOrder.order_date) >= start_date.date(),
            func.date(SalesOrder.order_date) <= end_date.date()
        )
        
        # Marketplace filter
        if marketplace and marketplace.lower() != "tümü":
            base_query = base_query.filter(SalesOrder.marketplace == marketplace)
        
        # Group by product
        product_metrics = base_query.group_by(
            SalesOrderItem.product_sku,
            SalesOrderItem.product_name,
            SalesOrderItem.barcode,
            SalesOrderItem.model_name
        ).all()
        
        # Calculate derived metrics
        products = []
        total_revenue = 0
        total_profit = 0
        
        # Batch olarak tüm SKU'ların görsellerini çek (performans için)
        # Hem tam SKU'ları hem de base SKU'ları sorgula
        from database.models import Product
        all_skus = [p.product_sku for p in product_metrics if p.total_quantity > 0]
        all_base_skus = [extract_base_sku(sku) for sku in all_skus if sku]
        # Combine and deduplicate - None'ları filtrele
        all_skus_to_query = list(set([s for s in (all_skus + all_base_skus) if s]))
        
        print(f"🔍 DEBUG: Total SKUs to query: {len(all_skus_to_query)}")
        print(f"   First 10 variant SKUs: {all_skus[:10]}")
        print(f"   First 10 base SKUs: {all_base_skus[:10]}")
        print(f"   285058 in query list: {'285058' in all_skus_to_query}")
        
        products_dict = {}
        if all_skus_to_query:
            products_batch = self.db.query(Product).filter(Product.sku.in_(all_skus_to_query)).all()
            products_dict = {p.sku: p for p in products_batch}
            print(f"🔍 DEBUG: Batch query returned {len(products_dict)} products")
            print(f"   285058 in results: {'285058' in products_dict}")
            logger.info(f"📷 Batch query: {len(all_skus_to_query)} SKUs queried, {len(products_dict)} products found")
        
        for p in product_metrics:
            # Skip if no sales
            if p.total_quantity == 0:
                continue
            
            # Mevcut total_cost_with_vat kullan (fallback dahil)
            # Calculate metrics
            profit = p.total_revenue - p.total_cost
            profit_margin = (profit / p.total_revenue * 100) if p.total_revenue > 0 else 0
            avg_profit_per_unit = profit / p.total_quantity if p.total_quantity > 0 else 0
            
            # Return rate
            total_sold = p.total_quantity + p.return_quantity
            return_rate = (p.return_quantity / total_sold * 100) if total_sold > 0 else 0
            
            # Sales velocity
            days_in_period = (end_date - start_date).days + 1
            daily_sales_avg = p.total_quantity / days_in_period if days_in_period > 0 else 0
            
            # Get current stock (simulated - gerçek stok API'den gelmeli)
            current_stock = self._get_stock(p.product_sku)
            days_of_stock = (current_stock / daily_sales_avg) if daily_sales_avg > 0 else None
            
            # Performance score (0-100)
            # Weighted: revenue 40%, profit_margin 30%, low_return_rate 20%, velocity 10%
            revenue_score = min(p.total_revenue / 10000 * 40, 40)  # 10K = max
            margin_score = min(profit_margin / 50 * 30, 30)  # 50% = max
            return_score = max(20 - (return_rate / 10 * 20), 0)  # 0% return = 20 points
            velocity_score = min(daily_sales_avg / 10 * 10, 10)  # 10/day = max
            
            performance_score = revenue_score + margin_score + return_score + velocity_score
            
            # Get product image - önce full SKU dene, sonra base SKU
            product_image = None
            prod = None
            base_sku = extract_base_sku(p.product_sku) if p.product_sku else None
            
            # İlk önce tam SKU ile dene
            if p.product_sku and p.product_sku in products_dict:
                prod = products_dict[p.product_sku]
                logger.debug(f"✅ Direct match: {p.product_sku}")
            # Bulamazsan base SKU ile dene
            elif base_sku and base_sku in products_dict:
                prod = products_dict[base_sku]
                logger.debug(f"✅ Base SKU match: {p.product_sku} -> {base_sku}")
            else:
                logger.debug(f"❌ No match: {p.product_sku} (base: {base_sku})")
            
            # Görsel var mı kontrol et
            if prod:
                if hasattr(prod, 'image') and prod.image:
                    product_image = prod.image
                    logger.debug(f"📷 Image found: {prod.sku} -> {product_image[:50]}...")
                elif hasattr(prod, 'image_url') and prod.image_url:
                    product_image = prod.image_url
            
            # Get brand
            brand = self._extract_brand(p.product_sku)
            
            products.append({
                "product_sku": p.product_sku,
                "product_name": p.product_name or "Ürün adı yok",
                "product_image": product_image,
                "brand": brand,
                "total_revenue": round(p.total_revenue, 2),
                "total_quantity": p.total_quantity,
                "total_orders": p.total_orders,
                "total_cost": round(p.total_cost, 2),
                "total_profit": round(profit, 2),
                "profit_margin": round(profit_margin, 2),
                "avg_profit_per_unit": round(avg_profit_per_unit, 2),
                "return_quantity": p.return_quantity,
                "return_rate": round(return_rate, 2),
                "return_revenue_loss": round(p.return_revenue_loss, 2),
                "current_stock": current_stock,
                "days_of_stock": round(days_of_stock, 1) if days_of_stock else None,
                "daily_sales_avg": round(daily_sales_avg, 2),
                "performance_score": round(performance_score, 2),
                "rank": 0  # Will be set after sorting
            })
            
            total_revenue += p.total_revenue
            total_profit += profit
        
        # Sort by selected criteria
        sort_key_map = {
            "revenue": lambda x: x["total_revenue"],
            "profit": lambda x: x["total_profit"],
            "quantity": lambda x: x["total_quantity"],
            "profit_margin": lambda x: x["profit_margin"]
        }
        
        sort_key = sort_key_map.get(sort_by, sort_key_map["revenue"])
        products.sort(key=sort_key, reverse=True)
        
        # Assign ranks
        for i, p in enumerate(products, 1):
            p["rank"] = i
        
        # Top N and worst N
        top_performers = products[:top_n]
        worst_performers = products[-top_n:][::-1]  # Reverse for worst-first
        
        # Re-rank worst performers (1 = worst)
        for i, p in enumerate(worst_performers, 1):
            p["rank"] = i
        
        # Overall stats
        avg_profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        return {
            "top_performers": top_performers,
            "worst_performers": worst_performers,
            "total_products": len(products),
            "date_range": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "days": (end_date - start_date).days + 1
            },
            "marketplace": marketplace or "Tümü",
            "total_revenue": round(total_revenue, 2),
            "total_profit": round(total_profit, 2),
            "avg_profit_margin": round(avg_profit_margin, 2)
        }
    
    def _get_stock(self, sku: str) -> int:
        """
        Stok bilgisi al (simulated)
        TODO: Gerçek stok API'sinden çek
        """
        # Simulated random stock
        import random
        random.seed(hash(sku))
        return random.randint(0, 500)
    
    def _get_product_image(self, sku: str) -> Optional[str]:
        """
        Ürün görseli al - Sentos API'den ilk görseli çek
        """
        # Cache'de var mı?
        if sku in self._image_cache:
            return self._image_cache[sku]
        
        try:
            # Sentos API'den ürün bilgisini çek
            from connectors.sentos_client import SentosClient
            from app.core import get_settings
            
            settings = get_settings()
            sentos = SentosClient(
                api_url=settings.sentos_api_url,
                api_key=settings.sentos_api_key,
                api_secret=settings.sentos_api_secret,
                api_cookie=settings.sentos_cookie
            )
            
            # SKU ile ürün ara
            product_data = sentos.get_product_by_sku(sku)
            
            if product_data:
                # İlk görseli al
                if 'image' in product_data and product_data['image']:
                    image_url = product_data['image']
                    self._image_cache[sku] = image_url
                    return image_url
                elif 'images' in product_data and len(product_data['images']) > 0:
                    image_url = product_data['images'][0]
                    if isinstance(image_url, dict) and 'url' in image_url:
                        image_url = image_url['url']
                    self._image_cache[sku] = image_url
                    return image_url
            
        except Exception as e:
            logger.debug(f"Could not fetch image for {sku}: {e}")
        
        # Cache'e None ekle (tekrar deneme)
        self._image_cache[sku] = None
        return None
    
    def _extract_brand(self, sku: str) -> Optional[str]:
        """
        SKU'dan brand çıkar
        BYK-25K-303760 → BYK
        """
        if not sku:
            return None
        
        parts = sku.split("-")
        if len(parts) > 0:
            return parts[0]
        
        return None
