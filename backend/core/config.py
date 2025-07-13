"""
Configuration module for MCP PCAP Reporter.
Uses Pydantic settings for environment variable management.
"""

from pydantic import validator
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
import ast
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "MCP PCAP Reporter"
    VERSION: str = "1.0.0"
    
    # Database Configuration
    DATABASE_URL: str = "mongodb://mongodb:27017/pcap_reporter"
    MONGO_PASSWORD: Optional[str] = None
    
    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    
    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if not v:
            return []
        if isinstance(v, str):
            try:
                # Safely evaluate string literal to a list
                return ast.literal_eval(v)
            except (ValueError, SyntaxError):
                # Fallback to comma-separated string
                return [i.strip() for i in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def assemble_allowed_hosts(cls, v: str | List[str]) -> List[str]:
        if not v:
            return []
        if isinstance(v, str):
            try:
                # Safely evaluate string literal to a list
                return ast.literal_eval(v)
            except (ValueError, SyntaxError):
                # Fallback to comma-separated string
                return [i.strip() for i in v.split(",")]
        return v
    
    # File Storage
    UPLOAD_PATH: str = "/app/uploads"
    LOG_PATH: str = "/app/logs"
    UPLOAD_MAX_SIZE: int = 104857600  # 100MB in bytes
    UPLOAD_ALLOWED_EXTENSIONS: List[str] = [".pcap", ".pcapng", ".cap"]
    
    # Analysis Settings
    MAX_CONCURRENT_ANALYSIS: int = 4
    ANALYSIS_TIMEOUT: int = 300  # 5 minutes
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Monitoring
    PROMETHEUS_PORT: int = 9090
    FLOWER_PORT: int = 5555
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


# The global settings instance is created here, which can be problematic for tests.
# It's better to create and inject the settings instance where needed.
# settings = Settings()


@lru_cache()
def get_settings() -> Settings:
    """
    Get the application settings.
    Uses lru_cache to ensure the Settings object is only created once.
    """
    return Settings() 