"""
Core Enums - Sentos API ve iş kuralları için sabitler
"""
from enum import Enum


class OrderStatus(int, Enum):
    """
    Sentos API Sipariş Durumları
    https://api.sentos.com.tr/docs
    """
    ONAY_BEKLIYOR = 1      # Onay Bekliyor
    ONAYLANDI = 2          # Onaylandı
    TEDARIK = 3            # Tedarik Sürecinde
    HAZIRLANIYOR = 4       # Hazırlanıyor
    KARGOYA_VERILDI = 5    # Kargoya Verildi (NORMAL - İADE DEĞİL!)
    IPTAL_IADE = 6         # İptal/İade Edildi
    TESLIM_EDILDI = 99     # Teslim Edildi


class ItemStatus(str, Enum):
    """
    Sipariş kalemi (item/line) durumları
    GERÇEK İADE TESPİTİ: item_status="rejected"
    """
    ACCEPTED = "accepted"   # Normal kabul edilmiş ürün
    REJECTED = "rejected"   # İade edilmiş ürün (GERÇEK İADE!)


class Marketplace(str, Enum):
    """
    Aktif satış kanalları
    ** RETAIL DAHİL DEĞİL **
    """
    TRENDYOL = "Trendyol"
    SHOPIFY = "Shopify"
    LC_WAIKIKI = "LCWaikiki"
    HEPSIBURADA = "Hepsiburada"
    PAZARAMA = "Pazarama"
    N11 = "N11"
    AMAZON = "Amazon"
    CICEKSEPETI = "CicekSepeti"
    
    @classmethod
    def get_all_values(cls):
        """Tüm marketplace isimlerini liste olarak döner"""
        return [m.value for m in cls]
    
    @classmethod
    def is_valid(cls, marketplace: str) -> bool:
        """Verilen marketplace geçerli mi kontrol eder"""
        if not marketplace:
            return False
        marketplace_upper = marketplace.upper()
        return any(m.value.upper() == marketplace_upper for m in cls)
    
    @classmethod
    def normalize(cls, marketplace: str) -> str:
        """Marketplace ismini standartlaştırır"""
        if not marketplace:
            return "UNKNOWN"
        
        marketplace_upper = marketplace.upper()
        
        mapping = {
            "TRENDYOL": cls.TRENDYOL.value,
            "SHOPIFY": cls.SHOPIFY.value,
            "LC WAIKIKI": cls.LC_WAIKIKI.value,
            "LCWAIKIKI": cls.LC_WAIKIKI.value,
            "LCW": cls.LC_WAIKIKI.value,
            "HEPSIBURADA": cls.HEPSIBURADA.value,
            "HB": cls.HEPSIBURADA.value,
            "PAZARAMA": cls.PAZARAMA.value,
            "N11": cls.N11.value,
            "AMAZON": cls.AMAZON.value,
            "CICEKSEPETI": cls.CICEKSEPETI.value,
            "ÇIÇEKSEPETI": cls.CICEKSEPETI.value,
        }
        
        return mapping.get(marketplace_upper, marketplace)


class MarketplaceCommission:
    """
    Marketplace komisyon oranları (%)
    
    Giyim kategorisi için komisyon oranları
    """
    COMMISSION_RATES = {
        "Trendyol": 21.5,      # Giyim kategorisi %21.5
        "Hepsiburada": 15.0,   # Örnek oran
        "N11": 12.0,           # Örnek oran
        "Pazarama": 18.0,      # Örnek oran
        "Shopify": 0.0,        # Kendi siteniz - komisyon yok
        "LCWaikiki": 0.0,      # Anlaşmalı - komisyon yok (veya farklı)
        "Amazon": 15.0,        # Örnek oran
        "CicekSepeti": 10.0,   # Örnek oran
    }
    
    @classmethod
    def get_rate(cls, marketplace: str) -> float:
        """
        Marketplace için komisyon oranını döner
        
        Args:
            marketplace: Marketplace adı (normalize edilmiş)
            
        Returns:
            Komisyon oranı (%) - Bulunamazsa 0.0
        """
        return cls.COMMISSION_RATES.get(marketplace, 0.0)
    
    @classmethod
    def calculate_commission(cls, marketplace: str, amount: float) -> float:
        """
        Komisyon tutarını hesaplar
        
        Args:
            marketplace: Marketplace adı
            amount: Net ciro
            
        Returns:
            Komisyon tutarı (TL)
        """
        rate = cls.get_rate(marketplace)
        return (amount * rate) / 100.0


class SalesChannel(str, Enum):
    """Satış kanalları - Retail filtreleme için"""
    ECOMMERCE = "ECOMMERCE"     # Sadece e-ticaret
    RETAIL = "RETAIL"            # Perakende (DAHİL OLMAYACAK)
    B2B = "B2B"                  # Toptan (opsiyonel)
