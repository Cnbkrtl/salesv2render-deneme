"""
17 Ekim Trendyol verilerini temizle ve yeniden çek
"""
from database import SessionLocal, SalesOrder, SalesOrderItem
from services.trendyol_data_fetcher import TrendyolDataFetcherService
from connectors.trendyol_client import TrendyolAPIClient
from datetime import datetime
from sqlalchemy import func, and_
import os
from dotenv import load_dotenv

load_dotenv()

db = SessionLocal()

# 1. 17 Ekim Trendyol verilerini temizle
print("🗑️  17 Ekim Trendyol verilerini temizliyorum...")
target_date = datetime(2025, 10, 17).date()

trendyol_orders = db.query(SalesOrder).filter(
    and_(
        SalesOrder.marketplace == 'Trendyol',
        func.date(SalesOrder.order_date) == target_date
    )
).all()

order_ids = [o.id for o in trendyol_orders]
print(f"  Bulunan sipariş: {len(order_ids)}")

if order_ids:
    items_deleted = db.query(SalesOrderItem).filter(
        SalesOrderItem.order_id.in_(order_ids)
    ).delete(synchronize_session=False)
    
    orders_deleted = db.query(SalesOrder).filter(
        SalesOrder.id.in_(order_ids)
    ).delete(synchronize_session=False)
    
    db.commit()
    print(f"✅ Temizlendi: {orders_deleted} sipariş, {items_deleted} item")
else:
    print("⚠️  Temizlenecek veri yok")

db.close()

# 2. Yeniden çek
print("\n🔄 17 Ekim verilerini yeniden çekiyorum...")

trendyol_client = TrendyolAPIClient(
    supplier_id=os.getenv('TRENDYOL_SUPPLIER_ID'),
    api_key=os.getenv('TRENDYOL_API_KEY'),
    api_secret=os.getenv('TRENDYOL_API_SECRET')
)

fetcher = TrendyolDataFetcherService(trendyol_client=trendyol_client)

# 17 Ekim 00:00 - 23:59
start_date = datetime(2025, 10, 17, 0, 0, 0)
end_date = datetime(2025, 10, 17, 23, 59, 59)

result = fetcher.fetch_and_store_trendyol_orders(
    start_date=start_date,
    end_date=end_date,
    statuses=None
)

print(f"\n✅ Sync tamamlandı!")
print(f"  Orders: {result.get('orders_fetched', 0)}")
print(f"  Items: {result.get('items_stored', 0)}")

# 3. Kontrol
db = SessionLocal()

orders = db.query(SalesOrder).filter(
    and_(
        SalesOrder.marketplace == 'Trendyol',
        func.date(SalesOrder.order_date) == target_date
    )
).all()

print(f"\n📊 Kontrol:")
print(f"  Sipariş sayısı: {len(orders)}")

# Status dağılımı
status_counts = {}
for order in orders:
    status_counts[order.order_status] = status_counts.get(order.order_status, 0) + 1

print(f"  Status dağılımı:")
for status, count in sorted(status_counts.items()):
    print(f"    Status {status}: {count} sipariş")

# Net ciro hesapla
iptal_iade_order_ids = set(o.id for o in orders if o.order_status == 6)
print(f"  İptal/İade: {len(iptal_iade_order_ids)} sipariş")

all_items = []
for order in orders:
    items = db.query(SalesOrderItem).filter(
        SalesOrderItem.order_id == order.id
    ).all()
    all_items.extend(items)

net_items = [item for item in all_items if item.order_id not in iptal_iade_order_ids]

net_ciro = sum(item.item_amount or 0 for item in net_items)

print(f"\n💰 CİRO:")
print(f"  Net Ciro (item_amount): {net_ciro:,.2f} TL")
print(f"  Beklenen: 67,832.00 TL")
print(f"  Fark: {net_ciro - 67832:,.2f} TL")

db.close()
