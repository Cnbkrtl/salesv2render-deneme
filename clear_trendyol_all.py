"""
RENDER'DA ÇALIŞTIR: Tüm Trendyol verilerini temizle

Bu script Render shell'de çalıştırılmalı:
1. Render Dashboard → Service → Shell
2. python clear_trendyol_all.py
"""
from database import SessionLocal, SalesOrder, SalesOrderItem
from sqlalchemy import and_

db = SessionLocal()

print("🗑️  TÜM Trendyol verilerini temizliyorum...")

# Trendyol siparişleri bul
trendyol_orders = db.query(SalesOrder).filter(
    SalesOrder.marketplace == 'Trendyol'
).all()

order_ids = [o.id for o in trendyol_orders]
print(f"📊 Bulunan Trendyol sipariş: {len(order_ids)}")

if order_ids:
    # Önce items
    items_deleted = db.query(SalesOrderItem).filter(
        SalesOrderItem.order_id.in_(order_ids)
    ).delete(synchronize_session=False)
    
    # Sonra orders
    orders_deleted = db.query(SalesOrder).filter(
        SalesOrder.id.in_(order_ids)
    ).delete(synchronize_session=False)
    
    db.commit()
    print(f"✅ Temizlendi!")
    print(f"   - Sipariş: {orders_deleted}")
    print(f"   - Item: {items_deleted}")
    print()
    print("🔄 Şimdi Admin Panel'den FULL RESYNC yapın!")
else:
    print("⚠️  Temizlenecek veri yok")

db.close()
