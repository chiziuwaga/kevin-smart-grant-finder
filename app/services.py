import os
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker # type: ignore
from utils.pinecone_client import PineconeClient
from utils.perplexity_client import PerplexityClient
from utils.notification_manager import NotificationManager
from config.settings import get_settings
import logging # Added logging import

logger = logging.getLogger(__name__) # Added logger instance

@dataclass
class Services:
    db_engine: AsyncSession = None # type: ignore
    db_sessionmaker: async_sessionmaker = None # type: ignore
    pinecone_client: PineconeClient = None
    perplexity_client: PerplexityClient = None
    notifier: NotificationManager = None
    start_time: float = None # type: ignore

services = Services()

async def init_services():
    import time
    services.start_time = time.time()
    settings = get_settings()
    
    # Initialize PostgreSQL
    # Use the db_url directly from settings - it already handles asyncpg format and SSL parameters
    db_url = settings.db_url

    services.db_engine = create_async_engine(db_url, echo=settings.app_debug)
    services.db_sessionmaker = async_sessionmaker(
        services.db_engine, 
        expire_on_commit=False,
        class_=AsyncSession
    )

    # Initialize Pinecone
    services.pinecone_client = PineconeClient() # API key and index name are read from env vars within the client
    # No explicit connect method in the provided PineconeClient, assuming it connects on demand or init

    # Initialize Perplexity
    services.perplexity_client = PerplexityClient() # API key is read from env vars within the client    # Initialize Notifications
    if settings.telegram_bot_token and settings.telegram_chat_id:
        services.notifier = NotificationManager(
            telegram_token=settings.telegram_bot_token,
            telegram_chat_id=settings.telegram_chat_id
        )
    else:
        logger.warning("Telegram token or chat ID not found in settings. NotificationManager not initialized.")
        services.notifier = None # Explicitly set to None if not configured

    logger.info("Service initialization completed successfully")