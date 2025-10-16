"""
FastAPI Main Application
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from datetime import datetime
import logging
import sys
import os

# Path setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core import get_settings
from app.api import health, data, analytics

# Import product_performance early
try:
    from app.api import product_performance
    HAS_PRODUCT_PERFORMANCE = True
except ImportError as e:
    HAS_PRODUCT_PERFORMANCE = False
    product_performance = None
    print(f"Warning: product_performance module not available: {e}")

# Logging - Create logs directory if it doesn't exist
log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    os.makedirs('logs', exist_ok=True)
    log_handlers.append(logging.FileHandler('logs/app.log', encoding='utf-8'))
except (OSError, PermissionError):
    # If we can't create logs directory (e.g., in read-only filesystem like Render),
    # just use stdout
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Log product_performance status
if HAS_PRODUCT_PERFORMANCE:
    logger.info("Product performance module available")
else:
    logger.warning("Product performance module not available")

# FastAPI App
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## Sales Analytics API v2
    
    **Yeni Ozellikler:**
    - Dogru status mapping (1-6, 99)
    - Retail filtreleme (sadece e-ticaret)
    - item_status="rejected" ile gercek iade tespiti
    - Kargo ucreti tracking
    - Urun maliyeti API'den cekme (%10 KDV'li)
    - Normalize database (orders + items ayri)
    - Brut/Net/Iptal-Iade hesaplamalari
    - Karlilik analizi
    
    **Metrikler:**
    - Brut Ciro (kargo dahil, iptal/iade dusulmemis)
    - Iptal/Iade Ciro (birlesik)
    - Net Ciro (kargo dahil, iptal/iade dusulmus)
    - Karlilik (Net ciro - maliyet - kargo gideri)
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - Frontend için yapılandırıldı
allowed_origins = [
    "http://localhost:5173",  # Vite default port (development)
    "http://localhost:3000",  # Alternative (development)
    "http://127.0.0.1:5173",  # Localhost (development)
    "https://sales-analytics-frontend.onrender.com",  # Production frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# API Key Security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """API key verification"""
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return api_key

# Startup
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Initialize database
    try:
        from database import Base, engine
        Base.metadata.create_all(bind=engine)
        logger.info("OK Database initialized")
    except Exception as e:
        logger.error(f"ERROR Database initialization error: {e}")
    
    # Start scheduled sync service
    try:
        from services.scheduled_sync import get_scheduler
        scheduler = get_scheduler()
        await scheduler.start()
        logger.info("✅ Scheduled sync service started")
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down...")
    
    # Stop scheduler
    try:
        from services.scheduled_sync import get_scheduler
        scheduler = get_scheduler()
        await scheduler.stop()
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")

# Root
@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "timestamp": datetime.utcnow()
    }

# Include routers
app.include_router(health.router)  # No auth required
app.include_router(data.router, dependencies=[Depends(verify_api_key)])
app.include_router(analytics.router, dependencies=[Depends(verify_api_key)])

# Sync Control Router
try:
    from app.api import sync
    app.include_router(sync.router, dependencies=[Depends(verify_api_key)])
    logger.info("Sync control router registered")
except Exception as e:
    logger.error(f"Failed to register sync router: {e}")

# Product Performance Router
if HAS_PRODUCT_PERFORMANCE and product_performance is not None:
    try:
        app.include_router(
            product_performance.router, 
            dependencies=[Depends(verify_api_key)]
        )
        logger.info(f"Product Performance router registered: {len(product_performance.router.routes)} routes")
        logger.info(f"   Prefix: {product_performance.router.prefix}")
        logger.info(f"   Routes: {[route.path for route in product_performance.router.routes]}")
    except Exception as e:
        logger.error(f"Failed to register product_performance router: {e}")
else:
    logger.warning("Product Performance router not registered (module not available)")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
