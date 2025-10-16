"""
Database initialization script
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine, Base
from database.models import Product, SalesOrder, SalesOrderItem, SalesMetricsCache


def init_database():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
    print("\nTables created:")
    print("  - products")
    print("  - sales_orders")
    print("  - sales_order_items")
    print("  - sales_metrics_cache")


if __name__ == "__main__":
    init_database()
