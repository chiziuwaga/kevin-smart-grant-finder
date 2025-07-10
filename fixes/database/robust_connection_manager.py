"""
Enhanced database connection management with retry logic and health monitoring.
Implements robust connection handling with graceful degradation.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import (
    AsyncEngine, 
    AsyncSession, 
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy import text, event
from sqlalchemy.exc import (
    SQLAlchemyError, 
    DisconnectionError, 
    OperationalError,
    DatabaseError
)

from config.settings import get_settings

logger = logging.getLogger(__name__)

@dataclass
class ConnectionHealth:
    """Track database connection health metrics"""
    is_healthy: bool = True
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    total_connections: int = 0
    active_connections: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    response_times: list = field(default_factory=list)
    
    def add_response_time(self, response_time: float):
        """Add response time and maintain rolling average"""
        self.response_times.append(response_time)
        if len(self.response_times) > 100:  # Keep last 100 measurements
            self.response_times.pop(0)
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time"""
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0.0

class RobustConnectionManager:
    """
    Enhanced database connection manager with retry logic, health monitoring,
    and graceful degradation capabilities.
    """
    
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.engine: Optional[AsyncEngine] = None
        self.sessionmaker: Optional[async_sessionmaker] = None
        self.health = ConnectionHealth()
        self.is_initialized = False
        self.initialization_lock = asyncio.Lock()
        self.max_retry_attempts = 3
        self.retry_delay = 1.0
        self.health_check_interval = 60.0  # seconds
        self.last_health_check = 0
        
        # Connection pool settings
        self.pool_size = 10
        self.max_overflow = 20
        self.pool_timeout = 30
        self.pool_recycle = 3600  # 1 hour
        
    async def initialize(self) -> bool:
        """
        Initialize database connection with retry logic.
        Returns True if successful, False otherwise.
        """
        async with self.initialization_lock:
            if self.is_initialized:
                return True
            
            logger.info("Initializing robust database connection manager...")
            
            for attempt in range(1, self.max_retry_attempts + 1):
                try:
                    await self._attempt_initialization()
                    self.is_initialized = True
                    self.health.is_healthy = True
                    self.health.consecutive_failures = 0
                    logger.info(f"Database connection initialized successfully on attempt {attempt}")
                    return True
                    
                except Exception as e:
                    self.health.consecutive_failures += 1
                    self.health.last_error = str(e)
                    logger.error(f"Database initialization attempt {attempt} failed: {e}")
                    
                    if attempt < self.max_retry_attempts:
                        delay = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                        logger.info(f"Retrying database initialization in {delay} seconds...")
                        await asyncio.sleep(delay)
                    else:
                        logger.critical("All database initialization attempts failed")
                        self.health.is_healthy = False
                        return False
            
            return False
    
    async def _attempt_initialization(self):
        """Attempt to initialize database connection"""
        # Create engine with enhanced settings
        connect_args = {
            "server_settings": {
                "application_name": "kevin-grant-finder",
                "connect_timeout": "30",
                "command_timeout": "30",
            }
        }
        
        # Choose pool class based on environment
        if self.settings.environment == "production":
            poolclass = QueuePool
        else:
            poolclass = NullPool
        
        self.engine = create_async_engine(
            self.settings.db_url,
            echo=self.settings.app_debug,
            poolclass=poolclass,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_timeout=self.pool_timeout,
            pool_recycle=self.pool_recycle,
            pool_pre_ping=True,  # Verify connections before use
            connect_args=connect_args
        )
        
        # Set up connection event handlers
        self._setup_connection_handlers()
        
        # Test connection
        async with self.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Create session maker
        self.sessionmaker = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
        
        logger.info("Database engine and sessionmaker created successfully")
    
    def _setup_connection_handlers(self):
        """Set up SQLAlchemy event handlers for connection monitoring"""
        if not self.engine:
            return
            
        @event.listens_for(self.engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            self.health.total_connections += 1
            self.health.active_connections += 1
            logger.debug(f"New database connection established. Active: {self.health.active_connections}")
        
        @event.listens_for(self.engine.sync_engine, "close")
        def on_close(dbapi_connection, connection_record):
            self.health.active_connections = max(0, self.health.active_connections - 1)
            logger.debug(f"Database connection closed. Active: {self.health.active_connections}")
        
        @event.listens_for(self.engine.sync_engine, "handle_error")
        def on_error(exception_context):
            self.health.error_count += 1
            self.health.last_error = str(exception_context.original_exception)
            logger.error(f"Database error occurred: {exception_context.original_exception}")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with automatic retry and health monitoring.
        """
        if not self.is_initialized:
            # Try to initialize if not already done
            if not await self.initialize():
                raise RuntimeError("Database not available - initialization failed")
        
        # Check if we need to perform health check
        current_time = time.time()
        if current_time - self.last_health_check > self.health_check_interval:
            await self._perform_health_check()
            self.last_health_check = current_time
        
        # If database is unhealthy, try to recover
        if not self.health.is_healthy:
            logger.warning("Database unhealthy, attempting recovery...")
            if not await self._attempt_recovery():
                raise RuntimeError("Database not available - health check failed")
        
        session = None
        start_time = time.time()
        
        try:
            if not self.sessionmaker:
                raise RuntimeError("Sessionmaker not initialized")
            session = self.sessionmaker()
            yield session
            await session.commit()
            
            # Record successful operation
            response_time = time.time() - start_time
            self.health.add_response_time(response_time)
            self.health.consecutive_failures = 0
            
        except Exception as e:
            self.health.consecutive_failures += 1
            self.health.error_count += 1
            self.health.last_error = str(e)
            
            if session:
                try:
                    await session.rollback()
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
            
            # Check if this is a connection-related error
            if isinstance(e, (DisconnectionError, OperationalError, DatabaseError)):
                logger.error(f"Database connection error: {e}")
                self.health.is_healthy = False
                
                # Try to recover for the next request
                asyncio.create_task(self._attempt_recovery())
            
            raise
        
        finally:
            if session:
                try:
                    await session.close()
                except Exception as close_error:
                    logger.error(f"Session close failed: {close_error}")
    
    async def _perform_health_check(self):
        """Perform database health check"""
        try:
            start_time = time.time()
            
            if not self.sessionmaker:
                raise RuntimeError("Sessionmaker not initialized")
            async with self.sessionmaker() as session:
                await session.execute(text("SELECT 1"))
                await session.execute(text("SELECT COUNT(*) FROM information_schema.tables"))
            
            response_time = time.time() - start_time
            self.health.add_response_time(response_time)
            self.health.last_check = datetime.utcnow()
            
            # Consider healthy if response time is reasonable
            if response_time < 5.0:  # 5 second threshold
                self.health.is_healthy = True
                self.health.consecutive_failures = 0
                logger.debug(f"Database health check passed in {response_time:.3f}s")
            else:
                logger.warning(f"Database health check slow: {response_time:.3f}s")
                
        except Exception as e:
            self.health.consecutive_failures += 1
            self.health.error_count += 1
            self.health.last_error = str(e)
            self.health.is_healthy = False
            logger.error(f"Database health check failed: {e}")
    
    async def _attempt_recovery(self) -> bool:
        """Attempt to recover from database issues"""
        logger.info("Attempting database recovery...")
        
        try:
            # Try to dispose and recreate engine
            if self.engine:
                await self.engine.dispose()
            
            # Reset state
            self.engine = None
            self.sessionmaker = None
            self.is_initialized = False
            
            # Try to reinitialize
            if await self.initialize():
                logger.info("Database recovery successful")
                return True
            else:
                logger.error("Database recovery failed")
                return False
                
        except Exception as e:
            logger.error(f"Database recovery error: {e}")
            return False
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status"""
        return {
            "is_healthy": self.health.is_healthy,
            "is_initialized": self.is_initialized,
            "last_check": self.health.last_check.isoformat() if self.health.last_check else None,
            "consecutive_failures": self.health.consecutive_failures,
            "total_connections": self.health.total_connections,
            "active_connections": self.health.active_connections,
            "error_count": self.health.error_count,
            "last_error": self.health.last_error,
            "avg_response_time": self.health.avg_response_time,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow
        }
    
    async def close(self):
        """Clean shutdown of database connections"""
        logger.info("Closing database connection manager...")
        
        if self.engine:
            try:
                await self.engine.dispose()
                logger.info("Database engine disposed successfully")
            except Exception as e:
                logger.error(f"Error disposing database engine: {e}")
        
        self.is_initialized = False
        self.health.is_healthy = False

# Global instance
_connection_manager: Optional[RobustConnectionManager] = None

async def get_connection_manager() -> RobustConnectionManager:
    """Get or create global connection manager"""
    global _connection_manager
    
    if _connection_manager is None:
        _connection_manager = RobustConnectionManager()
        await _connection_manager.initialize()
    
    return _connection_manager

async def get_robust_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function for FastAPI to get robust database session"""
    manager = await get_connection_manager()
    async for session in manager.get_session():
        yield session

@asynccontextmanager
async def database_transaction():
    """Context manager for database transactions with retry logic"""
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(1, max_retries + 1):
        try:
            manager = await get_connection_manager()
            async for session in manager.get_session():
                yield session
                return  # Success, exit retry loop
                
        except Exception as e:
            if attempt == max_retries:
                raise
            
            logger.warning(f"Transaction attempt {attempt} failed: {e}, retrying in {retry_delay}s")
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
