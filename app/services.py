import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy import text
from utils.pinecone_client import PineconeClient
from services.deepseek_client import DeepSeekClient
from services.resend_client import ResendEmailClient
from fixes.services.fallback_clients import (
    FallbackPineconeClient,
    FallbackNotificationManager
)
from config.settings import get_settings
import logging

logger = logging.getLogger(__name__)

@dataclass
class Services:
    db_engine: Optional[AsyncEngine] = None
    db_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None
    pinecone_client: Optional[Any] = None  # Can be PineconeClient or FallbackPineconeClient
    deepseek_client: Optional[DeepSeekClient] = None  # DeepSeek AI client
    notifier: Optional[Any] = None  # ResendEmailClient or FallbackNotificationManager
    start_time: Optional[float] = None

services = Services()

async def init_services():
    import time
    services.start_time = time.time()
    settings = get_settings()
    
    # Initialize PostgreSQL with robust error handling
    try:
        db_url = settings.db_url
        logger.info(f"Initializing database connection to: {db_url[:50]}...")
        
        services.db_engine = create_async_engine(
            db_url, 
            echo=settings.app_debug,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={
                "server_settings": {
                    "application_name": "kevin-grant-finder",
                }
            }
        )
        
        services.db_sessionmaker = async_sessionmaker(
            services.db_engine, 
            expire_on_commit=False,
            class_=AsyncSession
        )
        
        # Test database connection
        async with services.db_sessionmaker() as session:
            await session.execute(text("SELECT 1"))
            
        logger.info("Database connection established successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't raise - allow app to start with degraded functionality
        services.db_engine = None
        services.db_sessionmaker = None

    # Initialize Pinecone with fallback
    try:
        logger.info("Initializing Pinecone client...")
        services.pinecone_client = PineconeClient()
        logger.info("Pinecone client initialized successfully")
    except Exception as e:
        logger.warning(f"Pinecone initialization failed: {e}. Using fallback client.")
        services.pinecone_client = FallbackPineconeClient()

    # Initialize DeepSeek client
    try:
        logger.info("Initializing DeepSeek client...")
        services.deepseek_client = DeepSeekClient()
        logger.info("DeepSeek client initialized successfully")
    except Exception as e:
        logger.warning(f"DeepSeek initialization failed: {e}. AI features will be limited.")
        services.deepseek_client = None

    # Initialize Resend email client
    try:
        logger.info("Initializing Resend email client...")
        services.notifier = ResendEmailClient()
        logger.info("Resend email client initialized successfully")
    except Exception as e:
        logger.warning(f"Resend initialization failed: {e}. Using fallback notifier.")
        services.notifier = FallbackNotificationManager()

    logger.info("Service initialization completed with graceful degradation")