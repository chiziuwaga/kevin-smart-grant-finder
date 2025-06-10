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

    # API Keys
    pinecone_api_key: str = Field(default="", env="PINECONE_API_KEY")
    pinecone_index_name: str = Field(default="grantcluster", env="PINECONE_INDEX_NAME") # Corrected
    perplexity_api_key: str = Field(default="", env="PERPLEXITY_API_KEY")
    perplexity_rate_limit: int = Field(default=30, env="PERPLEXITY_RATE_LIMIT")
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")  # Added OpenAI API Key
    
    # Configuration File Paths
    PROJECT_ROOT: str = PROJECT_ROOT_PATH
    CONFIG_DIR: str = CONFIG_DIR_PATH
    KEVIN_PROFILE_CONFIG_PATH: str = os.path.join(CONFIG_DIR_PATH, "kevin_profile_config.yaml")
    COMPLIANCE_RULES_CONFIG_PATH: str = os.path.join(CONFIG_DIR_PATH, "compliance_rules_config.yaml")
    SECTOR_CONFIG_PATH: str = os.path.join(CONFIG_DIR_PATH, "sector_config.yaml")
    GEOGRAPHIC_CONFIG_PATH: str = os.path.join(CONFIG_DIR_PATH, "geographic_config.yaml")

    # Notifications
    telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN") # Changed from telegram_token
    telegram_chat_id: str = Field(default="", env="TELEGRAM_CHAT_ID")
    
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
              # Handle SSL parameters for asyncpg - remove ALL SSL params since Heroku handles this automatically
            # asyncpg will use SSL by default for Heroku Postgres
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