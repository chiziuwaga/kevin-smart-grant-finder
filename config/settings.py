"""
Application settings and configuration.
"""

import os
from functools import lru_cache
from typing import Any, Dict, Optional
from pydantic import Field, PostgresDsn, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Define Project Root and Config Directory
# Assuming settings.py is in the 'config' directory
CONFIG_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_PATH = os.path.dirname(CONFIG_DIR_PATH)

class DatabaseURL:
    """Helper class to build database URL."""
    @staticmethod
    def build_connection_string(
        user: str,
        password: str,
        host: str,
        port: int,
        db: str,
        async_driver: bool = True
    ) -> str:
        driver = "postgresql+asyncpg" if async_driver else "postgresql"
        return f"{driver}://{user}:{password}@{host}:{port}/{db}"

class Settings(BaseSettings):
    """Application settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"  # Allow extra fields for now
    )

    # Application
    app_debug: bool = Field(default=False)  # Renamed from debug
    environment: str = Field(default="development")
    secret_key: str = Field(default="default-secret-key")

    # Database
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_user: str = Field(default="postgres", env="DB_USER")
    db_pass: str = Field(default="", env="DB_PASSWORD")
    db_name: str = Field(default="grantfinder", env="DB_NAME")
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")

    # Legacy Auth0 (kept for migration compatibility, no longer used)
    AUTH0_DOMAIN: str = Field(default="", env="AUTH0_DOMAIN")
    AUTH0_API_AUDIENCE: str = Field(default="", env="AUTH0_API_AUDIENCE")
    AUTH0_ALGORITHMS: Optional[str] = Field(default="RS256", env="AUTH0_ALGORITHMS")

    # Payments (Stripe)
    STRIPE_SECRET_KEY: str = Field(default="", env="STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: str = Field(default="", env="STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field(default="", env="STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID: str = Field(default="", env="STRIPE_PRICE_ID")  # Price ID for $15/month plan

    # Email (Resend)
    RESEND_API_KEY: str = Field(default="", env="RESEND_API_KEY")
    FROM_EMAIL: str = Field(default="noreply@grantfinder.com", env="FROM_EMAIL")

    # Background Tasks (Celery/Redis)
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    CELERY_BROKER_URL: Optional[str] = Field(default=None, env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(default=None, env="CELERY_RESULT_BACKEND")

    # AI API Keys
    DEEPSEEK_API_KEY: str = Field(default="", env="DEEPSEEK_API_KEY")
    DEEPSEEK_API_BASE: str = Field(default="https://api.deepseek.com", env="DEEPSEEK_API_BASE")
    AGENTQL_API_KEY: str = Field(default="", env="AGENTQL_API_KEY")  # Web scraping for grant discovery

    # Authentication (simple JWT)
    SECRET_KEY: str = Field(default="change-me-in-production", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Configuration File Paths
    PROJECT_ROOT: str = PROJECT_ROOT_PATH
    CONFIG_DIR: str = CONFIG_DIR_PATH
    KEVIN_PROFILE_CONFIG_PATH: str = os.path.join(CONFIG_DIR_PATH, "kevin_profile_config.yaml")
    COMPLIANCE_RULES_CONFIG_PATH: str = os.path.join(CONFIG_DIR_PATH, "compliance_rules_config.yaml")
    SECTOR_CONFIG_PATH: str = os.path.join(CONFIG_DIR_PATH, "sector_config.yaml")
    GEOGRAPHIC_CONFIG_PATH: str = os.path.join(CONFIG_DIR_PATH, "geographic_config.yaml")

    # Frontend URL (for CORS)
    FRONTEND_URL: str = Field(default="http://localhost:3000", env="FRONTEND_URL")

    # Grant search configuration
    MAX_GRANTS_PER_SEARCH: int = Field(default=20, env="MAX_GRANTS_PER_SEARCH")

    @property
    def celery_broker(self) -> str:
        """Get Celery broker URL, defaults to REDIS_URL."""
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def celery_backend(self) -> str:
        """Get Celery result backend URL, defaults to REDIS_URL."""
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    @property
    def db_url(self) -> str:
        """Get the database URL, preferring DATABASE_URL if set, ensuring asyncpg format."""
        if self.database_url:
            url = str(self.database_url)  # Ensure it's a string
            
            # Convert to asyncpg format
            if "postgresql+asyncpg://" in url:
                return url
            elif "postgres://" in url:  # Handles 'postgres://'
                url = url.replace("postgres://", "postgresql+asyncpg://")
            elif "postgresql://" in url:  # Handles 'postgresql://'
                url = url.replace("postgresql://", "postgresql+asyncpg://")
            else:
                # This case implies an unsupported or malformed DATABASE_URL for asyncpg conversion
                raise ValueError(
                    f"DATABASE_URL ('{url}') is not in a recognized format to be converted to asyncpg. "
                    "Expected 'postgres://', 'postgresql://', or already async 'postgresql+asyncpg://'."
                )
              # Handle SSL parameters for asyncpg - remove SSL params that asyncpg doesn't support
            # asyncpg will use SSL by default for Render Postgres
            # Remove all possible SSL-related parameters
            import re
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            
            # Parse the URL to handle parameters properly
            parsed = urlparse(url)
            if parsed.query:
                # Parse query parameters
                params = parse_qs(parsed.query)
                
                # Remove all SSL-related parameters
                ssl_params = ['ssl', 'sslmode', 'sslcert', 'sslkey', 'sslrootcert']
                for param in ssl_params:
                    if param in params:
                        del params[param]
                
                # Rebuild the URL without SSL parameters
                new_query = urlencode(params, doseq=True)
                url = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment
                ))
            
            # Also handle simple string replacements for common patterns
            url = re.sub(r'[?&]ssl(mode)?=[^&]*', '', url)
            url = re.sub(r'[?&]sslcert=[^&]*', '', url)
            url = re.sub(r'[?&]sslkey=[^&]*', '', url)
            url = re.sub(r'[?&]sslrootcert=[^&]*', '', url)
            
            # Clean up any trailing ? or & characters
            url = url.rstrip('?&')
                
            return url
        else:
            # Build from components if DATABASE_URL is not set
            return DatabaseURL.build_connection_string(
                user=self.db_user,
                password=self.db_pass,
                host=self.db_host,
                port=self.db_port,
                db=self.db_name,
                async_driver=True
            )

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()