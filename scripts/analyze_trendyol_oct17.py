"""
17 Ekim Trendyol verilerini analiz et - İptal/İade kontrol
"""
from database import SessionLocal, SalesOrder, SalesOrderItem
from datetime import datetime
from sqlalchemy import func, and_

db = SessionLocal()

# 17 Ekim
target_date = datetime(2025, 10, 17).date()

orders = db.query(SalesOrder).filter(
    and_(
        SalesOrder.marketplace == 'Trendyol',
        func.date(SalesOrder.order_date) == target_date
    )
).all()

print(f'📊 17 EKİM TRENDYOL: {len(orders)} sipariş')
print('=' * 80)

# Status dağılımı
status_counts = {}
for order in orders:
    status = order.order_status
    status_counts[status] = status_counts.get(status, 0) + 1

print('📈 STATUS DAĞILIMI:')
status_names = {
    1: 'Onay Bekliyor',
    2: 'Onaylandı',
    3: 'Hazırlanıyor',
    4: 'Yola Çıktı',
    5: 'Kargoya Verildi',
    6: 'İptal/İade',
    99: 'Teslim Edildi'
}
for status, count in sorted(status_counts.items()):
    print(f'  {status_names.get(status, f"Status {status}")}: {count} sipariş')

print('\n' + '=' * 80)

# İptal/İade siparişleri (status == 6)
iptal_iade_orders = [o for o in orders if o.order_status == 6]
iptal_iade_order_ids = set(o.id for o in iptal_iade_orders)

print(f'❌ İPTAL/İADE: {len(iptal_iade_orders)} sipariş')
if iptal_iade_orders:
    print('\n📋 İptal/İade Detayları:')
    for order in iptal_iade_orders:
        items = db.query(SalesOrderItem).filter(
            SalesOrderItem.order_id == order.id
        ).all()
        
        total_gross = sum((item.unit_price or 0) * (item.quantity or 0) for item in items)
        total_commission = sum(item.commission_amount or 0 for item in items)
        total_net = sum(item.item_amount or 0 for item in items)
        
        print(f'  Sipariş: {order.trendyol_order_number}')
        print(f'    Status: {order.order_status} (İptal/İade)')
        print(f'    Items: {len(items)}')
        print(f'    Brüt: {total_gross:.2f} TL')
        print(f'    Komisyon: {total_commission:.2f} TL')
        print(f'    Net (item_amount): {total_net:.2f} TL')

print('\n' + '=' * 80)

# NET Siparişler (status != 6)
net_orders = [o for o in orders if o.order_status != 6]
print(f'✅ NET SİPARİŞLER: {len(net_orders)} sipariş')

# Tüm items
all_items = []
for order in orders:
    items = db.query(SalesOrderItem).filter(
        SalesOrderItem.order_id == order.id
    ).all()
    all_items.extend(items)

# İptal/İade items
iptal_iade_items = [item for item in all_items if item.order_id in iptal_iade_order_ids]
net_items = [item for item in all_items if item.order_id not in iptal_iade_order_ids]

# Hesaplamalar
total_gross = sum((item.unit_price or 0) * (item.quantity or 0) for item in all_items)
total_commission = sum(item.commission_amount or 0 for item in all_items)
total_item_amount = sum(item.item_amount or 0 for item in all_items)

net_gross = sum((item.unit_price or 0) * (item.quantity or 0) for item in net_items)
net_commission = sum(item.commission_amount or 0 for item in net_items)
net_item_amount = sum(item.item_amount or 0 for item in net_items)

iptal_gross = sum((item.unit_price or 0) * (item.quantity or 0) for item in iptal_iade_items)
iptal_commission = sum(item.commission_amount or 0 for item in iptal_iade_items)
iptal_item_amount = sum(item.item_amount or 0 for item in iptal_iade_items)

print('\n' + '=' * 80)
print('💰 CİRO ANALİZİ:')
print()
print('📊 TÜM SİPARİŞLER (İptal dahil):')
print(f'  Brüt Ciro: {total_gross:,.2f} TL')
print(f'  Komisyon: {total_commission:,.2f} TL')
print(f'  Item Amount (DB): {total_item_amount:,.2f} TL')
print(f'  Hesaplanan Net: {total_gross - total_commission:,.2f} TL')
print()
print('✅ NET SİPARİŞLER (İptal hariç):')
print(f'  Brüt Ciro: {net_gross:,.2f} TL')
print(f'  Komisyon: {net_commission:,.2f} TL')
print(f'  Item Amount (DB): {net_item_amount:,.2f} TL')
print(f'  Hesaplanan Net: {net_gross - net_commission:,.2f} TL')
print()
print('❌ İPTAL/İADE SİPARİŞLER:')
print(f'  Brüt Ciro: {iptal_gross:,.2f} TL')
print(f'  Komisyon: {iptal_commission:,.2f} TL')
print(f'  Item Amount (DB): {iptal_item_amount:,.2f} TL')
print()
print('=' * 80)
print('🎯 BEKLENEN:')
print(f'  Net Ciro: 67,832.00 TL (Trendyol paneli)')
print()
print(f'{"✅" if abs(net_item_amount - 67832) < 100 else "❌"} SONUÇ:')
print(f'  Hesaplanan Net: {net_item_amount:,.2f} TL')
print(f'  Fark: {net_item_amount - 67832:,.2f} TL')

db.close()
