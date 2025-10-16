"""
Prefix Discovery - Otomatik BYK prefix keşfi ve optimizasyonu
"""
from collections import Counter
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


def discover_byk_prefixes(product_cache: dict) -> List[str]:
    """
    Product cache'den otomatik BYK prefix'leri keşfet ve sıklığa göre sırala
    
    Args:
        product_cache: {sku: Product} dictionary
        
    Returns:
        Sıklığa göre sıralanmış prefix listesi
        Örnek: ['BYK-23Y', 'BYK-25K', 'BYK-24K', ...]
    """
    prefix_counter = Counter()
    
    for sku in product_cache.keys():
        if sku.startswith('BYK-'):
            parts = sku.split('-')
            if len(parts) >= 3:
                # BYK-23Y-303760 → BYK-23Y
                prefix = f"{parts[0]}-{parts[1]}"
                prefix_counter[prefix] += 1
    
    # En sık kullanılandan en aza sırala (top 20)
    sorted_prefixes = [prefix for prefix, count in prefix_counter.most_common(20)]
    
    logger.info(f"🔍 Discovered {len(sorted_prefixes)} BYK prefixes:")
    for idx, (prefix, count) in enumerate(prefix_counter.most_common(10)):
        logger.info(f"   {idx+1}. {prefix}: {count:,} products")
    
    return sorted_prefixes


def get_prefix_statistics(product_cache: dict) -> Dict:
    """
    Prefix istatistiklerini detaylı şekilde döner
    
    Returns:
        {
            'total_prefixes': int,
            'top_10': [(prefix, count), ...],
            'all_prefixes': {prefix: count, ...},
            'coverage': {
                'byk_products': int,
                'total_products': int,
                'percentage': float
            }
        }
    """
    prefix_counter = Counter()
    byk_product_count = 0
    
    for sku in product_cache.keys():
        if sku.startswith('BYK-'):
            byk_product_count += 1
            parts = sku.split('-')
            if len(parts) >= 3:
                prefix = f"{parts[0]}-{parts[1]}"
                prefix_counter[prefix] += 1
    
    total_products = len(product_cache)
    
    return {
        'total_prefixes': len(prefix_counter),
        'top_10': prefix_counter.most_common(10),
        'all_prefixes': dict(prefix_counter),
        'coverage': {
            'byk_products': byk_product_count,
            'total_products': total_products,
            'percentage': (byk_product_count / total_products * 100) if total_products > 0 else 0
        }
    }


def analyze_prefix_patterns(product_cache: dict) -> Dict:
    """
    Prefix paternlerini analiz et
    
    Returns:
        {
            'year_distribution': {'23': count, '24': count, ...},
            'season_distribution': {'Y': count, 'K': count},
            'recommendations': [str, ...]
        }
    """
    year_counter = Counter()
    season_counter = Counter()
    
    for sku in product_cache.keys():
        if sku.startswith('BYK-'):
            parts = sku.split('-')
            if len(parts) >= 2:
                season_code = parts[1]  # '23Y', '24K', etc.
                
                # Yıl bilgisi (ilk 2 karakter)
                if len(season_code) >= 2 and season_code[:2].isdigit():
                    year = season_code[:2]
                    year_counter[year] += 1
                
                # Sezon bilgisi (son karakter)
                if len(season_code) >= 1:
                    season = season_code[-1]
                    if season in ['Y', 'K']:  # Yaz / Kış
                        season_counter[season] += 1
    
    # Öneriler
    recommendations = []
    
    if len(year_counter) > 5:
        recommendations.append(
            f"⚠️ {len(year_counter)} farklı yıl bulundu. "
            "Eski yılları temizlemeyi düşünün."
        )
    
    if season_counter['Y'] + season_counter['K'] < sum(year_counter.values()) * 0.9:
        recommendations.append(
            "⚠️ Bazı ürünlerde sezon bilgisi eksik veya farklı format kullanılmış."
        )
    
    return {
        'year_distribution': dict(year_counter.most_common()),
        'season_distribution': dict(season_counter),
        'recommendations': recommendations
    }
