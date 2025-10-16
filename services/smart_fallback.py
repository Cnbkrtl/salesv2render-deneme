"""
Smart Fallback - Category-based fallback ratios
Improves fallback accuracy by using category/brand-specific ratios
"""
import logging
from typing import Dict, Optional
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class SmartFallback:
    """
    Smart fallback with category/brand-specific ratios
    Instead of flat 0.70, use actual data from matched items
    """
    
    def __init__(self):
        self.brand_ratios: Dict[str, float] = {}
        self.category_ratios: Dict[str, float] = {}
        self.default_ratio = 0.70
        self.min_samples = 10  # Minimum samples to trust ratio
        
    def calculate_ratios_from_data(self, sales_items: list):
        """
        Calculate cost/price ratios from successfully matched items
        
        Args:
            sales_items: List of SalesOrderItem objects with costs
        """
        # Collect ratios by brand
        brand_data = defaultdict(list)
        category_data = defaultdict(list)
        
        for item in sales_items:
            # Skip fallback items (cost_source == "FALLBACK")
            if hasattr(item, 'cost_source') and item.cost_source == "FALLBACK":
                continue
                
            # Skip if no valid data
            if not item.unit_cost_with_vat or not item.unit_price or item.unit_price == 0:
                continue
            
            ratio = item.unit_cost_with_vat / item.unit_price
            
            # Sanity check (ratio should be between 0.3 and 0.95)
            if 0.3 <= ratio <= 0.95:
                # Extract brand from SKU (e.g., "BYK-25K-..." → "BYK")
                sku = item.product_sku or ''
                parts = sku.split('-')
                if parts:
                    brand = parts[0]
                    brand_data[brand].append(ratio)
                
                # Category (if available in future)
                # category_data[item.category].append(ratio)
        
        # Calculate average ratios
        for brand, ratios in brand_data.items():
            if len(ratios) >= self.min_samples:
                avg_ratio = sum(ratios) / len(ratios)
                self.brand_ratios[brand] = round(avg_ratio, 3)
                logger.info(f"📊 Brand ratio calculated: {brand} = {avg_ratio:.3f} (from {len(ratios)} samples)")
        
        logger.info(f"✅ Smart fallback ratios calculated for {len(self.brand_ratios)} brands")
        
    def get_fallback_cost(
        self,
        unit_price: float,
        product_sku: Optional[str] = None,
        category: Optional[str] = None
    ) -> tuple[float, str]:
        """
        Get smart fallback cost based on brand/category
        
        Returns:
            (fallback_cost, ratio_source)
        """
        # Try brand-specific ratio
        if product_sku:
            parts = product_sku.split('-')
            if parts:
                brand = parts[0]
                if brand in self.brand_ratios:
                    ratio = self.brand_ratios[brand]
                    cost = unit_price * ratio
                    return (cost, f"BRAND_{brand}_{ratio}")
        
        # Try category-specific ratio (future)
        if category and category in self.category_ratios:
            ratio = self.category_ratios[category]
            cost = unit_price * ratio
            return (cost, f"CATEGORY_{category}_{ratio}")
        
        # Default fallback
        cost = unit_price * self.default_ratio
        return (cost, f"DEFAULT_{self.default_ratio}")
        
    def get_statistics(self) -> Dict:
        """Get fallback statistics"""
        return {
            'brand_ratios': self.brand_ratios,
            'category_ratios': self.category_ratios,
            'default_ratio': self.default_ratio,
            'brands_covered': len(self.brand_ratios),
            'categories_covered': len(self.category_ratios)
        }
        
    def print_report(self):
        """Print smart fallback statistics"""
        print("\n" + "="*80)
        print("🎯 SMART FALLBACK RATIOS")
        print("="*80)
        
        if self.brand_ratios:
            print(f"\n📊 Brand-specific ratios ({len(self.brand_ratios)} brands):")
            for brand, ratio in sorted(self.brand_ratios.items()):
                print(f"  • {brand}: {ratio:.3f} ({ratio*100:.1f}%)")
        else:
            print("\n⚠️ No brand-specific ratios yet (need more data)")
        
        print(f"\n🔧 Default fallback: {self.default_ratio:.3f} ({self.default_ratio*100:.1f}%)")
        print("="*80)


# Global instance
_smart_fallback = None

def get_smart_fallback() -> SmartFallback:
    """Get or create global smart fallback instance"""
    global _smart_fallback
    if _smart_fallback is None:
        _smart_fallback = SmartFallback()
    return _smart_fallback

def reset_smart_fallback():
    """Reset global smart fallback"""
    global _smart_fallback
    _smart_fallback = SmartFallback()
    return _smart_fallback
