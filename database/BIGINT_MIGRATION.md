# BIGINT Migration - Trendyol ID Overflow Fix

## Problem
```
❌ ERROR: integer out of range
PostgreSQL INTEGER limit: -2,147,483,648 to 2,147,483,647
Trendyol package ID: 3,288,955,360 (aşıyor!)
Cargo tracking: 7270027060328352 (16 haneli - aşıyor!)
```

## Root Cause
Trendyol API'den gelen bazı değerler PostgreSQL'in `INTEGER` tipinin limitini aşıyor:
- **Package IDs**: ~3.3 milyar (INT max: 2.1 milyar)
- **Cargo tracking numbers**: 16 haneli sayılar

## Solution
### 1. Model güncellemesi (`database/models.py`)
```python
# ÖNCE (INTEGER):
sentos_order_id = Column(Integer, ...)      # ❌ 2.1 milyar limit
order_code = Column(String(100), ...)        # ✅ String (karma: sayı veya text)
cargo_number = Column(String(100), ...)      # ❌ Sayı değil string olarak

# SONRA (BIGINT):
sentos_order_id = Column(BigInteger, ...)    # ✅ 9.2 quintillion limit
order_code = Column(String(100), ...)        # ✅ String KALSIN (karma kullanım)
cargo_number = Column(BigInteger, ...)       # ✅ Sayısal tip
```

**Not:** `order_code` string kaldı çünkü karma veri içeriyor:
- Eğer cargo tracking varsa: `7270027060328352` (sayısal)
- Eğer yoksa: `"10605513807"` (sipariş numarası - string)


### 2. Migration script (`database/migrate_bigint_ids.py`)
**PostgreSQL için:**
```sql
ALTER TABLE sales_orders ALTER COLUMN sentos_order_id TYPE BIGINT;
-- order_code SKIPPED (karma string/numeric veri)
ALTER TABLE sales_orders ALTER COLUMN cargo_number TYPE BIGINT 
  USING CASE WHEN cargo_number ~ '^[0-9]+$' THEN cargo_number::BIGINT ELSE NULL END;
ALTER TABLE sales_order_items ALTER COLUMN sentos_order_id TYPE BIGINT;
ALTER TABLE sales_order_items ALTER COLUMN sentos_item_id TYPE BIGINT;
```

**SQLite için:**
- SQLite'ın INTEGER tipi zaten 8 byte (BIGINT ile aynı)
- Migration gerekmez

## Deployment Steps

### Local (SQLite)
```bash
# Model zaten güncel, migration gerekmez
python -m uvicorn app.main:app --reload
```

### Production (PostgreSQL - Render)
```bash
# 1. Migration çalıştır
python database/migrate_bigint_ids.py

# 2. Servisi yeniden başlat
# (Render otomatik yapar)
```

## Data Type Limits

| Veritabanı | INTEGER | BIGINT |
|------------|---------|---------|
| PostgreSQL | 4 bytes (-2.1B to 2.1B) | 8 bytes (-9.2Q to 9.2Q) |
| SQLite | 8 bytes (BIGINT ile aynı) | 8 bytes |

**Q = Quintillion (10^18)**

## Affected Columns

### `sales_orders` table:
- ✅ `sentos_order_id` → BIGINT (Trendyol package ID)
- ⏭️ `order_code` → STRING (Mixed: cargo tracking OR order number)
- ✅ `cargo_number` → BIGINT (Cargo tracking number - nullable)

### `sales_order_items` table:
- ✅ `sentos_order_id` → BIGINT (Foreign key reference)
- ✅ `sentos_item_id` → BIGINT (Trendyol line item ID)

## Testing
```bash
# 1. Test migration
python database/migrate_bigint_ids.py

# 2. Test Trendyol sync
python -c "from services.trendyol_data_fetcher import TrendyolDataFetcher; \
from database import SessionLocal; \
db = SessionLocal(); \
fetcher = TrendyolDataFetcher(); \
from datetime import datetime; \
fetcher.fetch_and_store_trendyol_orders(db, datetime.now(), datetime.now())"
```

## Rollback (if needed)
```sql
-- PostgreSQL only (destructive if data > INT limit exists)
ALTER TABLE sales_orders ALTER COLUMN sentos_order_id TYPE INTEGER;
ALTER TABLE sales_orders ALTER COLUMN order_code TYPE VARCHAR(100);
ALTER TABLE sales_orders ALTER COLUMN cargo_number TYPE VARCHAR(100);
```

## Commit
```bash
git add database/models.py database/migrate_bigint_ids.py database/BIGINT_MIGRATION.md
git commit -m "fix: INTEGER overflow for Trendyol IDs - migrate to BIGINT"
git push origin main
```

---
**Date:** 2025-10-18  
**Issue:** `psycopg2.errors.NumericValueOutOfRange: integer out of range`  
**Status:** ✅ Fixed (Model updated, ready for production migration)
