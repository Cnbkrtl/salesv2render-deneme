"""
Database Connection
Supports both SQLite (dev) and PostgreSQL (production)
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sales_analytics_v2.db")

# PostgreSQL için özel ayarlar
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}
elif "postgresql" in DATABASE_URL:
    # Render PostgreSQL URL'si postgres:// ile başlayabilir, bunu düzelt
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    # PostgreSQL için connection pool ayarları
    pool_size = 10
    max_overflow = 20
else:
    pool_size = 10
    max_overflow = 20

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
    pool_size=pool_size if "postgresql" in DATABASE_URL else 5,
    max_overflow=max_overflow if "postgresql" in DATABASE_URL else 10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
