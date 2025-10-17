"""
Database Models - NORMALIZE VE OPTİMİZE EDİLMİŞ
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, DateTime, Text, Boolean, Index
)
from sqlalchemy.sql import func
from datetime import datetime

from .connection import Base


class Product(Base):
    """
    Ürün tablosu - Maliyet bilgilerini saklar
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sentos_product_id = Column(Integer, unique=True, index=True)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    
    # Product info
    name = Column(String(500))
    brand = Column(String(200))
    barcode = Column(String(100), index=True)
    image = Column(String(500))  # Ürün görseli URL
    
    # Cost information - MALİYET BİLGİSİ
    purchase_price = Column(Float, default=0.0)  # KDV'siz alış fiyatı
    vat_rate = Column(Integer, default=10)       # KDV oranı
    purchase_price_with_vat = Column(Float, default=0.0)  # KDV'li maliyet
    
    # Sales price (reference)
    sale_price = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_sku_lookup', 'sku'),
        Index('idx_barcode_lookup', 'barcode'),
    )


class SalesOrder(Base):
    """
    Sipariş tablosu - Temel sipariş bilgileri
    Her sipariş bir kez saklanır
    """
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)
    sentos_order_id = Column(Integer, unique=True, index=True, nullable=False)
    order_code = Column(String(100), index=True)
    
    # Trendyol-specific IDs (nullable for non-Trendyol orders)
    trendyol_shipment_package_id = Column(BigInteger, unique=True, index=True, nullable=True)
    trendyol_order_number = Column(String(50), index=True, nullable=True)
    
    # Order metadata
    order_date = Column(DateTime, nullable=False, index=True)
    marketplace = Column(String(50), nullable=False, index=True)
    shop = Column(String(200))
    
    # Status
    order_status = Column(Integer, nullable=False, index=True)  # 1-6, 99
    
    # Financial - ORDER LEVEL
    order_total = Column(Float, default=0.0)          # Sipariş toplamı (shipping dahil)
    shipping_total = Column(Float, default=0.0)       # Kargo ücreti (order level)
    carrying_charge = Column(Float, default=0.0)      # Taşıma bedeli
    service_fee = Column(Float, default=0.0)          # Hizmet bedeli
    
    # Kargo bilgileri
    cargo_provider = Column(String(100))
    cargo_number = Column(String(100))
    
    # Fatura
    has_invoice = Column(String(10))
    invoice_type = Column(String(50))
    invoice_number = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_order_date_marketplace', 'order_date', 'marketplace'),
        Index('idx_order_status', 'order_status'),
    )


class SalesOrderItem(Base):
    """
    Sipariş kalemi tablosu - HER ÜRÜN AYRI SATIRDA
    Normalized design - Join ile order'a bağlı
    """
    __tablename__ = "sales_order_items"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    order_id = Column(Integer, nullable=False, index=True)  # sales_orders.id ile join
    sentos_order_id = Column(Integer, nullable=False, index=True)  # Referans
    sentos_item_id = Column(Integer, index=True)
    
    # Trendyol-specific ID (nullable for non-Trendyol items)
    trendyol_order_line_id = Column(BigInteger, index=True, nullable=True)
    
    # Unique identifier
    unique_key = Column(String(200), unique=True, index=True, nullable=False)  # order_id_item_id
    
    # Product info
    product_name = Column(String(500))
    product_sku = Column(String(100), index=True)
    barcode = Column(String(100))
    color = Column(String(100))
    model_name = Column(String(100))
    model_value = Column(String(100))
    
    # Item status - GERÇEK İADE TESPİTİ
    item_status = Column(String(50), index=True)  # "accepted" veya "rejected"
    
    # Quantities
    quantity = Column(Integer, default=0)
    
    # Financial - ITEM LEVEL
    unit_price = Column(Float, default=0.0)
    item_amount = Column(Float, default=0.0)      # quantity * unit_price
    
    # Cost - ÜRÜN MALİYETİ (KDV'li)
    unit_cost_with_vat = Column(Float, default=0.0)
    total_cost_with_vat = Column(Float, default=0.0)  # unit_cost_with_vat * quantity
    
    # Commission (marketplace-specific)
    commission_rate = Column(Float, default=0.0)
    commission_amount = Column(Float, default=0.0)
    
    # Calculated fields - HESAPLANMIŞ DEĞERLER
    is_return = Column(Boolean, default=False)     # item_status="rejected"
    is_cancelled = Column(Boolean, default=False)   # order_status=6
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_item_order_lookup', 'order_id', 'sentos_order_id'),
        Index('idx_item_sku', 'product_sku'),
        Index('idx_item_status_return', 'item_status', 'is_return'),
    )


class SalesMetricsCache(Base):
    """
    Hesaplanmış metrikler için cache tablosu
    Performans için günlük/haftalık önceden hesaplanmış değerler
    """
    __tablename__ = "sales_metrics_cache"

    id = Column(Integer, primary_key=True, index=True)
    
    # Period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    marketplace = Column(String(50), index=True)  # NULL = all marketplaces
    
    # Brüt Metrikler
    brut_ciro = Column(Float, default=0.0)
    brut_siparis_sayisi = Column(Integer, default=0)
    brut_satilan_adet = Column(Integer, default=0)
    kargo_ucreti_toplam = Column(Float, default=0.0)
    
    # İptal/İade
    iptal_iade_ciro = Column(Float, default=0.0)
    iptal_iade_siparis_sayisi = Column(Integer, default=0)
    iptal_iade_adet = Column(Integer, default=0)
    
    # Net Metrikler
    net_ciro = Column(Float, default=0.0)
    net_siparis_sayisi = Column(Integer, default=0)
    net_satilan_adet = Column(Integer, default=0)
    
    # Karlılık
    urun_maliyeti_kdvli = Column(Float, default=0.0)
    kargo_gideri = Column(Float, default=0.0)
    kar = Column(Float, default=0.0)
    kar_marji = Column(Float, default=0.0)
    
    # Cache metadata
    is_valid = Column(Boolean, default=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_metrics_period', 'period_start', 'period_end', 'marketplace'),
    )
