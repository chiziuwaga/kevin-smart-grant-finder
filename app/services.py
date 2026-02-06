from dataclasses import dataclass
from typing import Optional, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy import text
from utils.pgvector_client import PgVectorClient
from services.deepseek_client import DeepSeekClient
from services.resend_client import ResendEmailClient
from fixes.services.fallback_clients import FallbackNotificationManager
from config.settings import get_settings
import logging

logger = logging.getLogger(__name__)

@dataclass
class Services:
    db_engine: Optional[AsyncEngine] = None
    db_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None
    vector_client: Optional[PgVectorClient] = None  # Postgres-backed vector store
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
        services.db_engine = None
        services.db_sessionmaker = None

    # Initialize PgVector client (Postgres-native vector store)
    try:
        logger.info("Initializing PgVector client...")
        services.vector_client = PgVectorClient(db_sessionmaker=services.db_sessionmaker)
        logger.info("PgVector client initialized successfully")
    except Exception as e:
        logger.warning(f"PgVector initialization failed: {e}. Using mock vector client.")
        services.vector_client = PgVectorClient()  # Falls back to mock mode

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