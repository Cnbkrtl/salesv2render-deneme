"""
Product Performance Analytics API
Ürün performans analizi - En iyi/en kötü performans gösteren ürünler
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Literal
from datetime import datetime, timedelta
from pydantic import BaseModel
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.product_performance import ProductPerformanceService

router = APIRouter(prefix="/api/product-performance", tags=["Product Performance"])


# Response Models
class ProductPerformanceItem(BaseModel):
    """Tek ürün performans detayı"""
    # Product info
    product_sku: str
    product_name: str
    product_image: Optional[str] = None
    brand: Optional[str] = None
    
    # Sales metrics
    total_revenue: float  # Toplam ciro
    total_quantity: int  # Toplam satılan adet
    total_orders: int  # Sipariş sayısı
    
    # Profitability
    total_cost: float  # Toplam maliyet
    total_profit: float  # Toplam kar
    profit_margin: float  # Kar marjı (%)
    avg_profit_per_unit: float  # Birim kar
    
    # Returns
    return_quantity: int  # İade adedi
    return_rate: float  # İade oranı (%)
    return_revenue_loss: float  # İade ciro kaybı
    
    # Stock & velocity
    current_stock: int  # Mevcut stok
    days_of_stock: Optional[float] = None  # Kaç günlük stok (satış hızına göre)
    daily_sales_avg: float  # Günlük ortalama satış
    
    # Performance score
    performance_score: float  # Genel performans skoru (0-100)
    rank: int  # Sıralama


class ProductPerformanceResponse(BaseModel):
    """Product performance API response"""
    # Top performers
    top_performers: List[ProductPerformanceItem]
    
    # Worst performers
    worst_performers: List[ProductPerformanceItem]
    
    # Summary
    total_products: int
    date_range: dict
    marketplace: Optional[str]
    
    # Aggregates
    total_revenue: float
    total_profit: float
    avg_profit_margin: float


def get_performance_service() -> ProductPerformanceService:
    """ProductPerformanceService dependency"""
    return ProductPerformanceService()


@router.get("/analyze", response_model=ProductPerformanceResponse)
async def analyze_product_performance(
    start_date: str = Query(..., description="Başlangıç tarihi (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Bitiş tarihi (YYYY-MM-DD)"),
    marketplace: Optional[str] = Query(None, description="Platform filtresi (Tümü için boş bırak)"),
    top_n: int = Query(20, ge=5, le=100, description="Kaç ürün gösterilsin (min=5, max=100)"),
    sort_by: Literal["revenue", "profit", "quantity", "profit_margin"] = Query(
        "revenue", 
        description="Sıralama kriteri"
    ),
    service: ProductPerformanceService = Depends(get_performance_service)
):
    """
    Ürün performans analizi
    
    **Top Performers:**
    - En çok ciro yapan
    - En karlı ürünler
    - En çok satılan
    
    **Worst Performers:**
    - En düşük performans
    - Yüksek iade oranı
    - Düşük kar marjı
    
    **Metrikler:**
    - Ciro, kar, kar marjı
    - İade oranı, iade zararı
    - Stok durumu, satış hızı
    - Günlük stok tükenme tahmini
    """
    try:
        # Date validation
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        if start > end:
            raise HTTPException(
                status_code=400,
                detail="Başlangıç tarihi bitiş tarihinden sonra olamaz"
            )
        
        # Call service
        result = service.analyze_performance(
            start_date=start,
            end_date=end,
            marketplace=marketplace,
            top_n=top_n,
            sort_by=sort_by
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Geçersiz tarih formatı: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analiz hatası: {str(e)}"
        )


@router.get("/top-sellers", response_model=List[ProductPerformanceItem])
async def get_top_sellers(
    start_date: str = Query(...),
    end_date: str = Query(...),
    marketplace: Optional[str] = Query(None),
    limit: int = Query(10, ge=5, le=50),
    service: ProductPerformanceService = Depends(get_performance_service)
):
    """En çok satanlar (sadece top performers)"""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        result = service.analyze_performance(
            start_date=start,
            end_date=end,
            marketplace=marketplace,
            top_n=limit,
            sort_by="revenue"
        )
        
        return result["top_performers"]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/worst-performers", response_model=List[ProductPerformanceItem])
async def get_worst_performers(
    start_date: str = Query(...),
    end_date: str = Query(...),
    marketplace: Optional[str] = Query(None),
    limit: int = Query(10, ge=5, le=50),
    service: ProductPerformanceService = Depends(get_performance_service)
):
    """En kötü performans gösterenler"""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        result = service.analyze_performance(
            start_date=start,
            end_date=end,
            marketplace=marketplace,
            top_n=limit,
            sort_by="revenue"
        )
        
        return result["worst_performers"]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
