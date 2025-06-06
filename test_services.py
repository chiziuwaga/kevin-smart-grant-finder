#!/usr/bin/env python3
"""
Test script to verify service initialization and connectivity
"""
import asyncio
import sys
import os
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services import init_services, services
from config.settings import get_settings
from config.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

async def test_services():
    """Test all service initializations"""
    print("=" * 50)
    print("KEVIN SMART GRANT FINDER - SERVICE WELLNESS CHECK")
    print("=" * 50)
    
    # Test settings loading
    print("\n1. Testing Settings Configuration...")
    try:
        settings = get_settings()
        print(f"✅ Settings loaded successfully")
        print(f"   - App Name: {settings.app_name}")
        print(f"   - Database URL: {settings.db_url[:50]}...")
        print(f"   - OpenAI API Key: {'*' * 20}...{settings.openai_api_key[-5:]}")
        print(f"   - Pinecone API Key: {'*' * 20}...{settings.pinecone_api_key[-5:]}")
        print(f"   - Perplexity API Key: {'*' * 20}...{settings.perplexity_api_key[-5:]}")
    except Exception as e:
        print(f"❌ Settings loading failed: {e}")
        return False
    
    # Test service initialization
    print("\n2. Testing Service Initialization...")
    try:
        await init_services()
        print(f"✅ Services initialized successfully")
        print(f"   - Services object: {type(services)}")
        print(f"   - DB Engine: {services.db_engine is not None}")
        print(f"   - DB SessionMaker: {services.db_sessionmaker is not None}")
        print(f"   - Pinecone Client: {services.pinecone_client is not None}")
        print(f"   - Perplexity Client: {services.perplexity_client is not None}")
        print(f"   - Notifier: {services.notifier is not None}")
        print(f"   - Start Time: {services.start_time}")
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        logger.error(f"Service initialization error: {e}", exc_info=True)
        return False
    
    # Test database connectivity
    print("\n3. Testing Database Connectivity...")
    try:
        if services.db_sessionmaker:
            async with services.db_sessionmaker() as session:
                result = await session.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                print(f"✅ Database connection successful: {row}")
        else:
            print("❌ Database sessionmaker not initialized")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        logger.error(f"Database connection error: {e}", exc_info=True)
    
    # Test Pinecone connectivity
    print("\n4. Testing Pinecone Connectivity...")
    try:
        if services.pinecone_client:
            # Test if we can access the index
            indexes = services.pinecone_client.list_indexes()
            print(f"✅ Pinecone connection successful")
            print(f"   - Available indexes: {[idx.name for idx in indexes]}")
        else:
            print("❌ Pinecone client not initialized")
    except Exception as e:
        print(f"❌ Pinecone connection failed: {e}")
        logger.error(f"Pinecone connection error: {e}", exc_info=True)
    
    # Test Perplexity connectivity
    print("\n5. Testing Perplexity Connectivity...")
    try:
        if services.perplexity_client:
            rate_limit = services.perplexity_client.get_rate_limit_status()
            print(f"✅ Perplexity client initialized")
            print(f"   - Rate limit status: {rate_limit}")
        else:
            print("❌ Perplexity client not initialized")
    except Exception as e:
        print(f"❌ Perplexity client test failed: {e}")
        logger.error(f"Perplexity client error: {e}", exc_info=True)
    
    # Test notification service
    print("\n6. Testing Notification Service...")
    try:
        if services.notifier:
            print(f"✅ Notification service initialized")
            print(f"   - Type: {type(services.notifier)}")
        else:
            print("⚠️ Notification service not initialized (may be expected if no Telegram config)")
    except Exception as e:
        print(f"❌ Notification service test failed: {e}")
        logger.error(f"Notification service error: {e}", exc_info=True)
    
    print("\n" + "=" * 50)
    print("SERVICE WELLNESS CHECK COMPLETED")
    print("=" * 50)
    return True

if __name__ == "__main__":
    # Import additional modules needed for database test
    from sqlalchemy import text
    
    try:
        result = asyncio.run(test_services())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        logger.error(f"Unexpected error in test: {e}", exc_info=True)
        sys.exit(1)
