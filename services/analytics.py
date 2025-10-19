"""
Analytics Service - BRÜT/NET HESAPLAMALAR
İade/İptal ayırma, karlılık, marketplace raporları
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from collections import defaultdict

from database import SalesOrder, SalesOrderItem, SessionLocal
from app.core import OrderStatus, ItemStatus, MarketplaceCommission

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Satış analizleri yapar"""
    
    def analyze_sales(
        self,
        start_date: str,
        end_date: str,
        marketplace: Optional[str] = None
    ) -> Dict:
        """
        Ana analiz fonksiyonu - YENİ GEREKSİNİMLERE GÖRE
        
        Returns:
            {
                'summary': {...},
                'by_marketplace': [...],
                'by_product': [...],
                'by_date': [...]
            }
        """
        db = SessionLocal()
        
        try:
            # Tarihleri parse et
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            
            # Orders ve items'ları çek
            orders, items = self._fetch_data(db, start_dt, end_dt, marketplace)
            
            if not items:
                return self._empty_response(start_date, end_date)
            
            # Analizler
            summary = self._calculate_summary(orders, items)
            by_marketplace = self._calculate_by_marketplace(orders, items)
            by_product = self._calculate_by_product(items)
            by_date = self._calculate_by_date(orders, items)
            
            return {
                'summary': summary,
                'by_marketplace': by_marketplace,
                'by_product': by_product,
                'by_date': by_date,
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'total_records': len(items),
                'generated_at': datetime.now()
            }
            
        finally:
            db.close()
    
    def _fetch_data(
        self,
        db: Session,
        start_dt: datetime,
        end_dt: datetime,
        marketplace: Optional[str] = None
    ):
        """Database'den verileri çeker"""
        
        # Orders
        orders_query = db.query(SalesOrder).filter(
            and_(
                SalesOrder.order_date >= start_dt,
                SalesOrder.order_date < end_dt
            )
        )
        
        if marketplace:
            orders_query = orders_query.filter(SalesOrder.marketplace == marketplace)
        
        orders = orders_query.all()
        order_ids = [o.id for o in orders]
        
        # Items
        items = []
        if order_ids:
            items = db.query(SalesOrderItem).filter(
                SalesOrderItem.order_id.in_(order_ids)
            ).all()
        
        logger.info(f"Fetched {len(orders)} orders, {len(items)} items")
        
        return orders, items
    
    def _calculate_summary(self, orders: List, items: List) -> Dict:
        """
        Özet metrikleri hesaplar - KAYNAK SİSTEMLE UYUMLU FORMÜL
        
        DOĞRU MANTIK:
        - İptal/İade = order_status == 6 olanlar (tüm order)
        - Satış (Net Ciro) = SADECE ÜRÜN CİROSU (kargo hariç!)
        - Brüt Ciro = Net + İptal/İade
        
        Returns:
            {
                'brut': {...},
                'iptal_iade': {...},
                'net': {...},
                'karlilik': {...}
            }
        """
        
        # 🎯 İPTAL/İADE = order_status == 6 olan SİPARİŞLER
        iptal_iade_order_ids = set()
        for order in orders:
            if order.order_status == 6:  # İptal/İade Edildi
                iptal_iade_order_ids.add(order.id)
        
        # İptal/İade items
        iptal_iade_items = [item for item in items if item.order_id in iptal_iade_order_ids]
        
        # Order -> Marketplace mapping
        order_to_mp = {order.id: order.marketplace for order in orders}
        
        # İptal/İade ciro - Komisyon düşülmeden
        iptal_iade_ciro = 0.0
        for item in iptal_iade_items:
            # TÜM marketplace'ler için komisyon düşülmez
            iptal_iade_ciro += (item.item_amount or 0.0)
        
        iptal_iade_adet = sum(item.quantity for item in iptal_iade_items)
        iptal_iade_siparis_sayisi = len(iptal_iade_order_ids)
        
        # Alt kırılım (opsiyonel - detay için)
        iptal_items = [item for item in iptal_iade_items if item.item_status == "accepted"]
        iade_items = [item for item in iptal_iade_items if item.item_status == "rejected"]
        
        # İptal/İade alt kırılımları - Komisyon düşülmeden
        iptal_ciro = sum(item.item_amount or 0.0 for item in iptal_items)
        iptal_adet = sum(item.quantity for item in iptal_items)
        
        iade_ciro = sum(item.item_amount or 0.0 for item in iade_items)
        iade_adet = sum(item.quantity for item in iade_items)
        
        # NET Metrikler (iptal/iade HARİÇ)
        net_items = [item for item in items if item.order_id not in iptal_iade_order_ids]
        
        net_satilan_adet = sum(item.quantity for item in net_items)
        
        # ÜRÜN CİROSU - Komisyon düşülmeden (Trendyol'dan alınan tutar)
        # ⚠️ ÖNEMLİ: Komisyon sadece KAR hesabında maliyet olarak kullanılır!
        # Trendyol: item_amount = Trendyol'dan alınan tutar (komisyon sonrası)
        # Diğerleri: item_amount = Marketplace'den alınan tutar
        net_ciro_urunler = 0.0
        order_to_mp = {order.id: order.marketplace for order in orders}
        for item in net_items:
            # TÜM marketplace'ler için item_amount olduğu gibi kullanılır
            # Komisyon ayrıca "Marketplace Komisyon" maliyet kalemi olarak gösterilir
            net_ciro_urunler += (item.item_amount or 0.0)
        
        # KARGO ÜCRETİ (order level) - Net siparişlerden
        net_orders = [order for order in orders if order.id not in iptal_iade_order_ids]
        net_kargo = sum(order.shipping_total for order in net_orders)
        
        # İptal/İade siparişlerin kargosu
        iptal_orders = [order for order in orders if order.id in iptal_iade_order_ids]
        iptal_kargo = sum(order.shipping_total for order in iptal_orders)
        
        # Toplam kargo (tüm siparişler)
        kargo_ucreti_toplam = sum(order.shipping_total for order in orders)
        
        # 📊 KAYNAK SİSTEM MANTIĞI:
        # Net Satış = Net Ürün + Net Kargo (iptal/iade HARİÇ!)
        # Brüt Satış = Net Satış + İptal/İade (ürün + kargo)
        net_ciro = net_ciro_urunler + net_kargo
        brut_ciro = net_ciro + iptal_iade_ciro + iptal_kargo
        
        # Brüt metrikler
        brut_satilan_adet = sum(item.quantity for item in items)
        brut_siparis_sayisi = len(set(order.id for order in orders))
        
        # Net sipariş sayısı (en az 1 net item'ı olan siparişler)
        net_order_ids = set(item.order_id for item in net_items)
        net_siparis_sayisi = len(net_order_ids)
        
        # KARLILIK Metrikleri
        # Ürün maliyeti (KDV'li) - sadece net items
        urun_maliyeti_kdvli = sum(item.total_cost_with_vat for item in net_items)
        
        # Kargo gideri - SABİT 75 TL per sipariş
        kargo_gideri = net_siparis_sayisi * 75.0
        
        # 🆕 MARKETPLACE KOMİSYON MALİYETİ
        # Her marketplace için komisyon hesapla
        marketplace_commissions = self._calculate_marketplace_commissions(orders, items)
        toplam_komisyon = sum(marketplace_commissions.values())
        
        # KAR = Net ciro - maliyet - kargo gideri - komisyon
        kar = net_ciro - urun_maliyeti_kdvli - kargo_gideri - toplam_komisyon
        
        # Kar marjı
        kar_marji = (kar / net_ciro * 100) if net_ciro > 0 else 0.0
        
        return {
            'brut': {
                'brut_ciro': round(brut_ciro, 2),
                'brut_siparis_sayisi': brut_siparis_sayisi,
                'brut_satilan_adet': brut_satilan_adet,
                'kargo_ucreti_toplam': round(kargo_ucreti_toplam, 2)
            },
            'iptal_iade': {
                'iptal_iade_ciro': round(iptal_iade_ciro, 2),
                'iptal_iade_siparis_sayisi': iptal_iade_siparis_sayisi,
                'iptal_iade_adet': iptal_iade_adet,
                'sadece_iptal_ciro': round(iptal_ciro, 2),
                'sadece_iptal_adet': iptal_adet,
                'sadece_iade_ciro': round(iade_ciro, 2),
                'sadece_iade_adet': iade_adet
            },
            'net': {
                'net_ciro': round(net_ciro, 2),
                'net_siparis_sayisi': net_siparis_sayisi,
                'net_satilan_adet': net_satilan_adet
            },
            'karlilik': {
                'urun_maliyeti_kdvli': round(urun_maliyeti_kdvli, 2),
                'kargo_gideri': round(kargo_gideri, 2),
                'marketplace_komisyon': round(toplam_komisyon, 2),  # 🆕 YENİ
                'marketplace_komisyon_detay': {  # 🆕 Detaylı breakdown
                    mp: round(amt, 2) for mp, amt in marketplace_commissions.items()
                },
                'kar': round(kar, 2),
                'kar_marji': round(kar_marji, 2)
            }
        }
    
    def _calculate_marketplace_commissions(self, orders: List, items: List) -> Dict[str, float]:
        """
        Marketplace bazlı komisyon hesaplar
        
        Returns:
            {
                'Trendyol': 258022.85,
                'Hepsiburada': 15000.00,
                ...
            }
        """
        commissions = defaultdict(float)
        
        # Order ID -> Marketplace mapping
        order_to_mp = {order.id: order.marketplace for order in orders}
        
        # 🆕 TRENDYOL için komisyon database'de var, diğerleri için hesaplıyoruz
        for item in items:
            # Sadece net items (iptal/iade hariç)
            if item.is_cancelled or item.is_return:
                continue
            
            marketplace = order_to_mp.get(item.order_id)
            if not marketplace:
                continue
            
            # Trendyol için komisyon zaten item.commission_amount'ta var
            if marketplace == 'Trendyol':
                commissions[marketplace] += (item.commission_amount or 0.0)
            else:
                # Diğer marketplace'ler için hesapla
                commissions[marketplace] += MarketplaceCommission.calculate_commission(
                    marketplace, 
                    item.item_amount
                ) / 100.0  # Rate'i amount'a uygula
        
        logger.debug(f"📊 Total commissions calculated: {commissions}")
        return dict(commissions)
    
    def _calculate_by_marketplace(self, orders: List, items: List) -> List[Dict]:
        """Marketplace bazlı analiz"""
        
        # Group by marketplace
        mp_data = defaultdict(lambda: {
            'orders': [],
            'items': []
        })
        
        # Orders'ları grupla
        for order in orders:
            mp = order.marketplace
            mp_data[mp]['orders'].append(order)
        
        # Items'ları grupla (join through order_id)
        order_to_mp = {order.id: order.marketplace for order in orders}
        for item in items:
            mp = order_to_mp.get(item.order_id)
            if mp:
                mp_data[mp]['items'].append(item)
        
        # Her marketplace için hesapla
        result = []
        for marketplace, data in mp_data.items():
            mp_orders = data['orders']
            mp_items = data['items']
            
            if not mp_items:
                continue
            
            # Summary hesapla (aynı mantık)
            summary = self._calculate_summary(mp_orders, mp_items)
            
            result.append({
                'marketplace': marketplace,
                **summary
            })
        
        return sorted(result, key=lambda x: x['net']['net_ciro'], reverse=True)
    
    def _calculate_by_product(self, items: List) -> List[Dict]:
        """Ürün bazlı analiz"""
        
        # Group by product
        product_data = defaultdict(lambda: {
            'product_name': '',
            'sku': '',
            'items': []
        })
        
        for item in items:
            key = item.product_sku or item.product_name
            product_data[key]['product_name'] = item.product_name
            product_data[key]['sku'] = item.product_sku or ''
            product_data[key]['items'].append(item)
        
        # Her ürün için hesapla
        result = []
        for key, data in product_data.items():
            items_list = data['items']
            
            # Net items (iptal/iade hariç)
            net_items = [i for i in items_list if not i.is_cancelled and not i.is_return]
            
            if not net_items:
                continue
            
            net_satilan_adet = sum(i.quantity for i in net_items)
            net_ciro = sum(i.item_amount for i in net_items)
            maliyet = sum(i.total_cost_with_vat for i in net_items)
            kar = net_ciro - maliyet
            kar_marji = (kar / net_ciro * 100) if net_ciro > 0 else 0.0
            
            result.append({
                'product_name': data['product_name'],
                'sku': data['sku'],
                'net_satilan_adet': net_satilan_adet,
                'net_ciro': round(net_ciro, 2),
                'maliyet': round(maliyet, 2),
                'kar': round(kar, 2),
                'kar_marji': round(kar_marji, 2)
            })
        
        return sorted(result, key=lambda x: x['net_ciro'], reverse=True)[:100]
    
    def _calculate_by_date(self, orders: List, items: List) -> List[Dict]:
        """Tarih bazlı analiz"""
        
        # Group by date
        date_data = defaultdict(lambda: {
            'orders': [],
            'items': []
        })
        
        # Orders'ları grupla
        for order in orders:
            date_key = order.order_date.strftime('%Y-%m-%d')
            date_data[date_key]['orders'].append(order)
        
        # Items'ları grupla
        order_to_date = {order.id: order.order_date.strftime('%Y-%m-%d') for order in orders}
        for item in items:
            date_key = order_to_date.get(item.order_id)
            if date_key:
                date_data[date_key]['items'].append(item)
        
        # Her gün için hesapla
        result = []
        for date_str, data in date_data.items():
            date_items = data['items']
            date_orders = data['orders']
            
            # Net items
            net_items = [i for i in date_items if not i.is_cancelled and not i.is_return]
            
            if not net_items:
                net_ciro = 0.0
                net_siparis_sayisi = 0
                net_satilan_adet = 0
            else:
                net_satilan_adet = sum(i.quantity for i in net_items)
                net_ciro_urunler = sum(i.item_amount for i in net_items)
                kargo = sum(o.shipping_total for o in date_orders)
                net_ciro = net_ciro_urunler + kargo
                
                net_order_ids = set(i.order_id for i in net_items)
                net_siparis_sayisi = len(net_order_ids)
            
            result.append({
                'date': date_str,
                'net_ciro': round(net_ciro, 2),
                'net_siparis_sayisi': net_siparis_sayisi,
                'net_satilan_adet': net_satilan_adet
            })
        
        return sorted(result, key=lambda x: x['date'])
    
    def _empty_response(self, start_date: str, end_date: str) -> Dict:
        """Boş response döner"""
        return {
            'summary': {
                'brut': {
                    'brut_ciro': 0.0,
                    'brut_siparis_sayisi': 0,
                    'brut_satilan_adet': 0,
                    'kargo_ucreti_toplam': 0.0
                },
                'iptal_iade': {
                    'iptal_iade_ciro': 0.0,
                    'iptal_iade_siparis_sayisi': 0,
                    'iptal_iade_adet': 0,
                    'sadece_iptal_ciro': 0.0,
                    'sadece_iptal_adet': 0,
                    'sadece_iade_ciro': 0.0,
                    'sadece_iade_adet': 0
                },
                'net': {
                    'net_ciro': 0.0,
                    'net_siparis_sayisi': 0,
                    'net_satilan_adet': 0
                },
                'karlilik': {
                    'urun_maliyeti_kdvli': 0.0,
                    'kargo_gideri': 0.0,
                    'kar': 0.0,
                    'kar_marji': 0.0
                }
            },
            'by_marketplace': [],
            'by_product': [],
            'by_date': [],
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'total_records': 0,
            'generated_at': datetime.now()
        }
