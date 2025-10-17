"""
Migration: Add Trendyol columns to sales_orders table

This migration adds:
- trendyol_shipment_package_id (BigInteger, unique, nullable)
- trendyol_order_number (String, nullable)

Usage:
    python -m database.migrate_add_trendyol_columns
"""

import os
import sys
from sqlalchemy import text, inspect
from database.connection import engine, SessionLocal

def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate():
    """Add Trendyol columns if they don't exist"""
    
    db = SessionLocal()
    
    try:
        # Check database type
        db_url = str(engine.url)
        is_postgresql = 'postgresql' in db_url
        is_sqlite = 'sqlite' in db_url
        
        print(f"🔍 Database type: {'PostgreSQL' if is_postgresql else 'SQLite' if is_sqlite else 'Unknown'}")
        print(f"📍 Database URL: {db_url}")
        
        # Check if columns exist
        has_shipment_id = check_column_exists('sales_orders', 'trendyol_shipment_package_id')
        has_order_number = check_column_exists('sales_orders', 'trendyol_order_number')
        
        print(f"\n📊 Current state:")
        print(f"  - trendyol_shipment_package_id: {'✅ EXISTS' if has_shipment_id else '❌ MISSING'}")
        print(f"  - trendyol_order_number: {'✅ EXISTS' if has_order_number else '❌ MISSING'}")
        
        if has_shipment_id and has_order_number:
            print("\n✅ All columns already exist. No migration needed.")
            return
        
        print("\n🔄 Starting migration...")
        
        # Add trendyol_shipment_package_id
        if not has_shipment_id:
            print("  📝 Adding trendyol_shipment_package_id...")
            if is_postgresql:
                db.execute(text("""
                    ALTER TABLE sales_orders 
                    ADD COLUMN trendyol_shipment_package_id BIGINT UNIQUE
                """))
                db.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_trendyol_shipment_package_id 
                    ON sales_orders(trendyol_shipment_package_id)
                """))
            else:  # SQLite
                db.execute(text("""
                    ALTER TABLE sales_orders 
                    ADD COLUMN trendyol_shipment_package_id INTEGER
                """))
            db.commit()
            print("     ✅ Added trendyol_shipment_package_id")
        
        # Add trendyol_order_number
        if not has_order_number:
            print("  📝 Adding trendyol_order_number...")
            if is_postgresql:
                db.execute(text("""
                    ALTER TABLE sales_orders 
                    ADD COLUMN trendyol_order_number VARCHAR(50)
                """))
                db.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_trendyol_order_number 
                    ON sales_orders(trendyol_order_number)
                """))
            else:  # SQLite
                db.execute(text("""
                    ALTER TABLE sales_orders 
                    ADD COLUMN trendyol_order_number TEXT
                """))
            db.commit()
            print("     ✅ Added trendyol_order_number")
        
        print("\n✅ Migration completed successfully!")
        
        # Verify
        has_shipment_id = check_column_exists('sales_orders', 'trendyol_shipment_package_id')
        has_order_number = check_column_exists('sales_orders', 'trendyol_order_number')
        
        print(f"\n📊 Final state:")
        print(f"  - trendyol_shipment_package_id: {'✅ EXISTS' if has_shipment_id else '❌ MISSING'}")
        print(f"  - trendyol_order_number: {'✅ EXISTS' if has_order_number else '❌ MISSING'}")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 80)
    print("🔄 MIGRATION: Add Trendyol columns to sales_orders")
    print("=" * 80)
    migrate()
    print("=" * 80)
