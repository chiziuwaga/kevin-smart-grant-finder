import os
from dataclasses import dataclass
from utils.mongodb_client import MongoDBClient
from utils.pinecone_client import PineconeClient
from utils.perplexity_client import PerplexityClient
from utils.notification_manager import NotificationManager
from config.settings import load_settings

@dataclass
class Services:
    mongodb_client: MongoDBClient = None
    pinecone_client: PineconeClient = None
    perplexity_client: PerplexityClient = None
    notifier: NotificationManager = None

services = Services()

async def init_services():
    # Load settings
    settings = load_settings()
    
    # Initialize MongoDB
    services.mongodb_client = MongoDBClient(
        uri=os.getenv("MONGODB_URI", settings.mongodb.uri)
    )
    await services.mongodb_client.connect()

    # Initialize Pinecone
    services.pinecone_client = PineconeClient(
        api_key=os.getenv("PINECONE_API_KEY", settings.pinecone.api_key),
        index_name=os.getenv("PINECONE_INDEX", settings.pinecone.index_name)
    )
    await services.pinecone_client.connect()

    # Initialize Perplexity
    services.perplexity_client = PerplexityClient(
        api_key=os.getenv("PERPLEXITY_API_KEY", settings.perplexity.api_key)
    )

    # Initialize Notifications
    services.notifier = NotificationManager(
        telegram_token=os.getenv("TELEGRAM_TOKEN", settings.telegram.token),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", settings.telegram.chat_id)
    )