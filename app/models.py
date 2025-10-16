"""
Pydantic Models - Request/Response schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


# ============================================================================
# REQUEST MODELS
# ============================================================================

class FetchDataRequest(BaseModel):
    """Veri çekme isteği"""
    start_date: str = Field(..., description="Başlangıç tarihi (YYYY-MM-DD)")
    end_date: str = Field(..., description="Bitiş tarihi (YYYY-MM-DD)")
    marketplace: Optional[str] = Field(None, description="Marketplace filtresi")
    clear_existing: bool = Field(False, description="Mevcut verileri temizle")


class AnalyticsRequest(BaseModel):
    """Analiz isteği"""
    start_date: str = Field(..., description="Başlangıç tarihi (YYYY-MM-DD)")
    end_date: str = Field(..., description="Bitiş tarihi (YYYY-MM-DD)")
    marketplace: Optional[str] = Field(None, description="Marketplace filtresi")


# ============================================================================
# RESPONSE MODELS - YENİ GEREKSİNİMLERE GÖRE
# ============================================================================

class BrutMetrics(BaseModel):
    """Brüt Metrikler (iptal/iade düşülmemiş)"""
    brut_ciro: float = Field(..., description="Brüt ciro (kargo dahil, iptal/iade düşülmemiş)")
    brut_siparis_sayisi: int = Field(..., description="Brüt sipariş sayısı")
    brut_satilan_adet: int = Field(..., description="Brüt satılan adet")
    kargo_ucreti_toplam: float = Field(..., description="Siparişlerden alınan kargo ücreti")


class IptalIadeMetrics(BaseModel):
    """İptal/İade Metrikleri (birleşik)"""
    iptal_iade_ciro: float = Field(..., description="İptal + İade toplam tutar")
    iptal_iade_siparis_sayisi: int = Field(..., description="İptal + İade sipariş sayısı")
    iptal_iade_adet: int = Field(..., description="İptal + İade adet")
    
    # Detay (opsiyonel)
    sadece_iptal_ciro: float = 0.0
    sadece_iptal_adet: int = 0
    sadece_iade_ciro: float = 0.0
    sadece_iade_adet: int = 0


class NetMetrics(BaseModel):
    """Net Metrikler (iptal/iade düşülmüş, kargo dahil)"""
    net_ciro: float = Field(..., description="Net ciro (brüt - iptal/iade, kargo dahil)")
    net_siparis_sayisi: int = Field(..., description="Net sipariş sayısı")
    net_satilan_adet: int = Field(..., description="Net satılan adet")


class KarlilikMetrics(BaseModel):
    """Karlılık Metrikleri"""
    urun_maliyeti_kdvli: float = Field(..., description="Satılan ürünlerin %10 KDV'li maliyeti")
    kargo_gideri: float = Field(..., description="Kargo giderleri toplamı")
    kar: float = Field(..., description="Net ciro - maliyet - kargo = KAR")
    kar_marji: float = Field(..., description="Kar marjı yüzdesi")


class SummaryResponse(BaseModel):
    """Özet rapor - YENİ FORMATTA"""
    brut: BrutMetrics
    iptal_iade: IptalIadeMetrics
    net: NetMetrics
    karlilik: KarlilikMetrics


class MarketplaceMetrics(BaseModel):
    """Marketplace bazlı metrikler"""
    marketplace: str
    brut: BrutMetrics
    iptal_iade: IptalIadeMetrics
    net: NetMetrics
    karlilik: KarlilikMetrics


class ProductMetrics(BaseModel):
    """Ürün bazlı metrikler"""
    product_name: str
    sku: str
    net_satilan_adet: int
    net_ciro: float
    maliyet: float
    kar: float
    kar_marji: float


class DailyMetrics(BaseModel):
    """Günlük metrikler"""
    date: str
    net_ciro: float
    net_siparis_sayisi: int
    net_satilan_adet: int


class AnalyticsResponse(BaseModel):
    """Ana analiz response"""
    summary: SummaryResponse
    by_marketplace: List[MarketplaceMetrics]
    by_product: List[ProductMetrics]
    by_date: List[DailyMetrics]
    
    # Metadata
    period: Dict[str, str]
    total_records: int
    generated_at: datetime


class FetchDataResponse(BaseModel):
    """Veri çekme response"""
    success: bool
    records_fetched: int
    records_stored: int
    message: str
    duration_seconds: float


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    sentos_connection: str
    database_connection: str
    version: str
