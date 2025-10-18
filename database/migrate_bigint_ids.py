"""
Migration: Convert INTEGER columns to BIGINT for Trendyol large IDs
Fix: integer out of range error for package IDs and cargo numbers
"""
from sqlalchemy import create_engine, text
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_to_bigint():
    """
    Trendyol'dan gelen büyük sayıları desteklemek için INTEGER -> BIGINT dönüşümü
    
    Problem kolonlar:
    - sales_orders.sentos_order_id (Trendyol package ID olarak kullanılıyor)
    - sales_orders.order_code (Cargo tracking number - 16 haneli)
    - sales_orders.cargo_number (Cargo tracking number - 16 haneli)
    
    PostgreSQL INTEGER limit: -2,147,483,648 to 2,147,483,647
    Trendyol package IDs: ~3,288,955,360 (INTEGER limitini aşıyor!)
    Cargo tracking numbers: 7270027060328352 (16 hane - INTEGER limitini aşıyor!)
    """
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sales_analytics_v2.db")
    
    # PostgreSQL URL düzeltme
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(DATABASE_URL)
    
    is_sqlite = "sqlite" in DATABASE_URL
    
    if is_sqlite:
        logger.info("⚠️ SQLite detected - SQLite INTEGER already supports up to 8 bytes (same as BIGINT)")
        logger.info("ℹ️  SQLite INTEGER = 8 bytes (up to 9,223,372,036,854,775,807)")
        logger.info("ℹ️  No migration needed for SQLite!")
        logger.info("✅ Models updated, migration will run on PostgreSQL production deployment")
        return
    
    # PostgreSQL migration
    with engine.connect() as conn:
        try:
            logger.info("🔧 Starting BIGINT migration for PostgreSQL...")
            
            logger.info("📊 Converting sentos_order_id to BIGINT...")
            conn.execute(text("""
                ALTER TABLE sales_orders 
                ALTER COLUMN sentos_order_id TYPE BIGINT
            """))
            conn.commit()
            logger.info("✅ sentos_order_id -> BIGINT")
            
            # SKIP order_code - it contains mixed data (numeric cargo_tracking OR string order_number)
            logger.info("⏭️  Skipping order_code (contains mixed string/numeric data)")
            
            logger.info("📊 Converting cargo_number to BIGINT...")
            conn.execute(text("""
                ALTER TABLE sales_orders 
                ALTER COLUMN cargo_number TYPE BIGINT 
                USING CASE 
                    WHEN cargo_number ~ '^[0-9]+$' THEN cargo_number::BIGINT 
                    ELSE NULL 
                END
            """))
            conn.commit()
            logger.info("✅ cargo_number -> BIGINT (non-numeric values set to NULL)")
            
            # sentos_order_items tablosundaki ilgili kolonlar
            logger.info("📊 Converting sales_order_items.sentos_order_id to BIGINT...")
            conn.execute(text("""
                ALTER TABLE sales_order_items 
                ALTER COLUMN sentos_order_id TYPE BIGINT
            """))
            conn.commit()
            logger.info("✅ sales_order_items.sentos_order_id -> BIGINT")
            
            logger.info("📊 Converting sales_order_items.sentos_item_id to BIGINT...")
            conn.execute(text("""
                ALTER TABLE sales_order_items 
                ALTER COLUMN sentos_item_id TYPE BIGINT
            """))
            conn.commit()
            logger.info("✅ sales_order_items.sentos_item_id -> BIGINT")
            
            logger.info("🎉 PostgreSQL migration completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            conn.rollback()
            raise


if __name__ == "__main__":
    migrate_to_bigint()
