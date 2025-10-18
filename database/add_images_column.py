"""
Migration: Add images column to products table
Production database'de eksik kolon için
"""
import os
import sys
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings

def migrate():
    """Add images column to products table"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Check if column exists
        try:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='products' AND column_name='images'
            """))
            
            if result.fetchone():
                print("✅ Column 'images' already exists!")
                return
        except Exception as e:
            print(f"⚠️ Could not check column (might be SQLite): {e}")
        
        # Add column
        try:
            print("📝 Adding 'images' column to products table...")
            conn.execute(text("""
                ALTER TABLE products 
                ADD COLUMN images TEXT DEFAULT '[]'
            """))
            conn.commit()
            print("✅ Column 'images' added successfully!")
        except Exception as e:
            print(f"❌ Error adding column: {e}")
            print("💡 If column already exists, this is normal.")

if __name__ == "__main__":
    migrate()
