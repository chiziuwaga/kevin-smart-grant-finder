"""
Database session management and connection handling.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.db_url,  # Corrected: Use the db_url property
    echo=settings.app_debug,  # Corrected: Use app_debug
    future=True,
    poolclass=NullPool
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
