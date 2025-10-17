"""
Migration: Add images JSON column to products table

This migration adds an 'images' column to store multiple product images as JSON array.
Supports both PostgreSQL (JSONB) and SQLite (TEXT).

Usage:
    python -m database.migrate_add_images_json
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from sqlalchemy import text, inspect
from database.connection import engine, SessionLocal
from app.core.config import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if column exists in table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate():
    """Add images JSON column to products table"""
    
    settings = get_settings()
    db = SessionLocal()
    
    try:
        logger.info("🔄 Starting migration: Add images JSON column")
        logger.info(f"Database: {settings.database_url[:30]}...")
        
        # Detect database type
        db_url = str(settings.database_url).lower()
        is_postgres = 'postgresql' in db_url
        is_sqlite = 'sqlite' in db_url
        
        logger.info(f"Database type: {'PostgreSQL' if is_postgres else 'SQLite' if is_sqlite else 'Unknown'}")
        
        # Check if products table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'products' not in tables:
            logger.warning("⚠️ products table does not exist, skipping migration")
            return
        
        # Check if column already exists
        if check_column_exists('products', 'images'):
            logger.info("✅ Column 'images' already exists, skipping")
            return
        
        # Add column based on database type
        if is_postgres:
            logger.info("Adding 'images' column as JSONB (PostgreSQL)")
            db.execute(text("""
                ALTER TABLE products 
                ADD COLUMN images JSONB DEFAULT '[]'::jsonb
            """))
            logger.info("✅ Column 'images' added (JSONB)")
            
        elif is_sqlite:
            logger.info("Adding 'images' column as TEXT (SQLite)")
            db.execute(text("""
                ALTER TABLE products 
                ADD COLUMN images TEXT DEFAULT '[]'
            """))
            logger.info("✅ Column 'images' added (TEXT)")
            
        else:
            logger.error("❌ Unsupported database type")
            return
        
        db.commit()
        logger.info("✅ Migration completed successfully")
        
        # Migrate existing image data
        logger.info("🔄 Migrating existing image data...")
        
        if is_postgres:
            result = db.execute(text("""
                UPDATE products 
                SET images = jsonb_build_array(image)
                WHERE image IS NOT NULL AND image != '' AND images = '[]'::jsonb
            """))
        else:  # SQLite
            result = db.execute(text("""
                UPDATE products 
                SET images = json_array(image)
                WHERE image IS NOT NULL AND image != '' AND images = '[]'
            """))
        
        db.commit()
        
        rows_updated = result.rowcount
        logger.info(f"✅ Migrated {rows_updated} existing image(s) to images array")
        
        # Show sample
        sample = db.execute(text("SELECT sku, image, images FROM products WHERE images != '[]' LIMIT 3")).fetchall()
        if sample:
            logger.info("📸 Sample migrated images:")
            for row in sample:
                logger.info(f"  SKU: {row[0]} | Old: {row[1][:50] if row[1] else 'None'}... | New: {row[2]}")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
        
    finally:
        db.close()


if __name__ == "__main__":
    try:
        migrate()
        logger.info("✅ All done!")
    except Exception as e:
        logger.error(f"❌ Migration script failed: {e}")
        sys.exit(1)
