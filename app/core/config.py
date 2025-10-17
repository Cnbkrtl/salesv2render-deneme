"""
Application Configuration
Çevre değişkenlerinden yapılandırma yüklenir
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Uygulama ayarları"""
    
    # Application
    app_name: str = "Sales Analytics API v2"
    app_version: str = "2.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Sentos API
    sentos_api_url: str
    sentos_api_key: str
    sentos_api_secret: str
    sentos_cookie: Optional[str] = None
    
    # Trendyol API
    trendyol_api_url: str = "https://apigw.trendyol.com"
    trendyol_supplier_id: Optional[str] = None
    trendyol_api_key: Optional[str] = None
    trendyol_api_secret: Optional[str] = None
    
    # Database
    database_url: str = "sqlite:///./sales_analytics_v2.db"
    
    # Security
    api_key: str
    
    # CORS
    allowed_origins: str = "*"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Settings singleton"""
    return Settings()
