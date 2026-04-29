"""
Configuration module

Loads environment variables and exposes settings via Pydantic.
"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Authentication
    AUTH_TOKEN: str = ""
    
    # MEXC API
    MEXC_API_KEY: str = ""
    MEXC_API_SECRET: str = ""
    
    # Trading configuration
    ACCOUNT_RISK: float = 15.0
    MAX_ACTIVE_POSITIONS: int = 1
    DEFAULT_LEVERAGE: int = 10
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Redis (optional)
    REDIS_URL: Optional[str] = None
    
    # Alerts
    TOKENS: str = "ETH,SOL,LINK,SUI,TAO"
    SIGNAL_TYPES: str = "OG,FVG,ChoCh,ADX"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()
