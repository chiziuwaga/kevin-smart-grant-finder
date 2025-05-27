"""
Application settings and configuration.
"""

import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Dict, Optional

# Load environment variables
load_dotenv()

# Database settings
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'grantfinder'),
    'user': os.getenv('DB_USER', 'user'),
    'password': os.getenv('DB_PASSWORD', '')
}

# API settings
GRANTS_API_KEY = os.getenv('GRANTS_API_KEY')

# Application settings
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
APP_ENV = os.getenv('APP_ENV', 'development')

class MongoDBSettings(BaseModel):
    uri: str = Field("mongodb://localhost:27017", description="MongoDB connection URI")
    database: str = Field("grant_finder", description="Database name")

class PineconeSettings(BaseModel):
    api_key: str = Field("", description="Pinecone API key")
    index_name: str = Field("grants", description="Pinecone index name")

class PerplexitySettings(BaseModel):
    api_key: str = Field("", description="Perplexity API key")
    rate_limit: int = Field(30, description="Rate limit per minute")

class TelegramSettings(BaseModel):
    token: str = Field("", description="Telegram bot token")
    chat_id: str = Field("", description="Telegram chat ID")

class Settings(BaseModel):
    """Main settings container"""
    environment: str = Field("development", description="Environment (development/production)")
    mongodb: MongoDBSettings = Field(default_factory=MongoDBSettings)
    pinecone: PineconeSettings = Field(default_factory=PineconeSettings)
    perplexity: PerplexitySettings = Field(default_factory=PerplexitySettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def load_settings() -> Settings:
    """Load settings from environment variables"""
    return Settings()