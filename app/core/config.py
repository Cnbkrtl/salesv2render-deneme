"""
Application Configuration
Çevre değişkenlerinden yapılandırma yüklenir
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
from pydantic import Field


class Settings(BaseSettings):
    """Uygulama ayarları"""
    
    # Application

    app_name: str = Field("Sales Analytics API v2", alias="APP_NAME")
    app_version: str = Field("2.0.0", alias="APP_VERSION")
    debug: bool = Field(False, alias="DEBUG")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # Server
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8000, alias="PORT")

    # Sentos API
    sentos_api_url: str = Field(..., alias="SENTOS_API_URL")
    sentos_api_key: str = Field(..., alias="SENTOS_API_KEY")
    sentos_api_secret: str = Field(..., alias="SENTOS_API_SECRET")
    sentos_cookie: Optional[str] = Field(None, alias="SENTOS_COOKIE")

    # Trendyol API
    trendyol_api_url: str = Field("https://apigw.trendyol.com", alias="TRENDYOL_API_URL")
    trendyol_supplier_id: Optional[str] = Field(None, alias="TRENDYOL_SUPPLIER_ID")
    trendyol_api_key: Optional[str] = Field(None, alias="TRENDYOL_API_KEY")
    trendyol_api_secret: Optional[str] = Field(None, alias="TRENDYOL_API_SECRET")

    # Database
    database_url: str = Field("sqlite:///./sales_analytics_v2.db", alias="DATABASE_URL")

    # Security
    api_key: str = Field(..., alias="API_KEY")

    # CORS
    allowed_origins: str = Field("*", alias="ALLOWED_ORIGINS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_prefix = ""


@lru_cache()
def get_settings() -> Settings:
    """Settings singleton"""
    return Settings()
