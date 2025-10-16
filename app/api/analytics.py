"""
Analytics Endpoints
Satış analizleri ve raporlama
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import csv
import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models import AnalyticsRequest, AnalyticsResponse
from services.analytics import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def get_analytics_service() -> AnalyticsService:
    """AnalyticsService dependency"""
    return AnalyticsService()


@router.post("/analyze", response_model=AnalyticsResponse)
async def analyze_sales(
    request: AnalyticsRequest,
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    """
    Satış verilerini analiz eder
    
    **Metrikler:**
    
    **BRÜT:**
    - Brüt Ciro: Tüm siparişler + kargo (iptal/iade düşülmemiş)
    - Brüt Sipariş Sayısı
    - Brüt Satılan Adet
    - Kargo Ücreti Toplamı
    
    **İPTAL/İADE:**
    - İptal/İade Ciro (birleşik)
    - İptal/İade Sipariş Sayısı
    - İptal/İade Adet
    
    **NET:**
    - Net Ciro: Brüt - İptal/İade (kargo dahil!)
    - Net Sipariş Sayısı
    - Net Satılan Adet
    
    **KARLILIK:**
    - Ürün Maliyeti (KDV'li %10)
    - Kargo Gideri
    - Kar: Net ciro - maliyet - kargo gideri
    - Kar Marjı %
    """
    try:
        result = analytics.analyze_sales(
            start_date=request.start_date,
            end_date=request.end_date,
            marketplace=request.marketplace
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/csv")
async def export_csv(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    marketplace: Optional[str] = Query(None),
    analytics: AnalyticsService = Depends(get_analytics_service)
):
    """
    Analiz sonuçlarını CSV olarak export eder
    """
    try:
        result = analytics.analyze_sales(start_date, end_date, marketplace)
        
        # CSV oluştur
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Metrik', 'Değer'])
        
        # Brüt
        writer.writerow(['=== BRÜT METRİKLER ===', ''])
        for key, value in result['summary']['brut'].items():
            writer.writerow([key, value])
        
        # İptal/İade
        writer.writerow(['', ''])
        writer.writerow(['=== İPTAL/İADE ===', ''])
        for key, value in result['summary']['iptal_iade'].items():
            writer.writerow([key, value])
        
        # Net
        writer.writerow(['', ''])
        writer.writerow(['=== NET METRİKLER ===', ''])
        for key, value in result['summary']['net'].items():
            writer.writerow([key, value])
        
        # Karlılık
        writer.writerow(['', ''])
        writer.writerow(['=== KARLILIK ===', ''])
        for key, value in result['summary']['karlilik'].items():
            writer.writerow([key, value])
        
        # Marketplace detay
        writer.writerow(['', ''])
        writer.writerow(['=== MARKETPLACE BAZINDA ===', ''])
        writer.writerow(['Marketplace', 'Net Ciro', 'Net Sipariş', 'Kar', 'Kar Marjı %'])
        for mp in result['by_marketplace']:
            writer.writerow([
                mp['marketplace'],
                mp['net']['net_ciro'],
                mp['net']['net_siparis_sayisi'],
                mp['karlilik']['kar'],
                mp['karlilik']['kar_marji']
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=sales_analytics_{start_date}_{end_date}.csv"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
