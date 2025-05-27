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

services = Services()

async def init_services():
    settings = get_settings()
    
    # Initialize PostgreSQL
    # Ensure db_url is correctly formatted for asyncpg
    db_url = settings.db_url 
    if "postgres://" in db_url and "postgresql+asyncpg://" not in db_url:
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://")
    elif "postgresql://" in db_url and "postgresql+asyncpg://" not in db_url:
         # if it's just postgresql://, it might be missing the +asyncpg part
        if "+asyncpg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

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
    services.perplexity_client = PerplexityClient() # API key is read from env vars within the client

    # Initialize Notifications
    if settings.telegram_bot_token and settings.telegram_chat_id:
        services.notifier = NotificationManager(
            telegram_token=settings.telegram_bot_token,
            telegram_chat_id=settings.telegram_chat_id
        )
    else:
        logger.warning("Telegram token or chat ID not found in settings. NotificationManager not initialized.")
        services.notifier = None # Explicitly set to None if not configured

    # The following line can be removed if Home.py has its own separate initialization logic
    # or if it also relies on this central init_services.
    # pass # Service initialization is now primarily handled in Home.py