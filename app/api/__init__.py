"""API module"""
# Import all routers
from . import health, data, analytics, product_performance

__all__ = ["health", "data", "analytics", "product_performance"]
