import os
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from utils.pinecone_client import PineconeClient
from utils.perplexity_client import PerplexityClient
from utils.notification_manager import NotificationManager
from config.settings import get_settings # Corrected import

@dataclass
class Services:
    db_engine: AsyncSession = None
    db_sessionmaker: async_sessionmaker = None
    pinecone_client: PineconeClient = None
    perplexity_client: PerplexityClient = None
    notifier: NotificationManager = None

services = Services()

async def init_services():
    # Load settings
    # settings = get_settings()
    
    # # Initialize PostgreSQL
    # database_url = os.getenv("DATABASE_URL", settings.postgres.url)
    # if not database_url.startswith('postgresql+asyncpg://'):
    #     database_url = f"postgresql+asyncpg://{database_url.split('://', 1)[1]}"
    
    # services.db_engine = create_async_engine(database_url, echo=True)
    # services.db_sessionmaker = async_sessionmaker(
    #     services.db_engine, 
    #     expire_on_commit=False
    # )

    # # Initialize Pinecone
    # services.pinecone_client = PineconeClient(
    #     api_key=os.getenv("PINECONE_API_KEY", settings.pinecone.api_key),
    #     index_name=os.getenv("PINECONE_INDEX", settings.pinecone.index_name)
    # )
    # await services.pinecone_client.connect()

    # # Initialize Perplexity
    # services.perplexity_client = PerplexityClient(
    #     api_key=os.getenv("PERPLEXITY_API_KEY", settings.perplexity.api_key)
    # )

    # # Initialize Notifications
    # services.notifier = NotificationManager(
    #     telegram_token=os.getenv("TELEGRAM_TOKEN", settings.telegram.token),
    #     telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", settings.telegram.chat_id)
    # )
    pass # Service initialization is now primarily handled in Home.py