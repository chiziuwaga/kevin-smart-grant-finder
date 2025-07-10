"""
Database health monitoring and recovery utilities.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class DatabaseHealthMonitor:
    """Monitor database health and provide recovery capabilities."""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.last_health_check = None
        self.health_status = "unknown"
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.health_check_interval = 30  # seconds
        self.is_monitoring = False
        
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive database health check."""
        health_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unknown",
            "checks": {},
            "metrics": {}
        }
        
        if not self.session_factory:
            health_info["status"] = "unavailable"
            health_info["checks"]["session_factory"] = "missing"
            return health_info
        
        try:
            async with self.session_factory() as session:
                # Test basic connectivity
                start_time = datetime.utcnow()
                await session.execute(text("SELECT 1"))
                response_time = (datetime.utcnow() - start_time).total_seconds()
                
                health_info["checks"]["connectivity"] = "healthy"
                health_info["metrics"]["response_time_seconds"] = response_time
                
                # Check table existence and counts
                tables_to_check = ["grants", "analyses", "search_runs", "user_settings"]
                table_info = {}
                
                for table in tables_to_check:
                    try:
                        result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        table_info[table] = {"status": "healthy", "count": count}
                    except SQLAlchemyError as e:
                        table_info[table] = {"status": "error", "error": str(e)}
                
                health_info["checks"]["tables"] = table_info
                
                # Check for recent activity
                try:
                    recent_cutoff = datetime.utcnow() - timedelta(hours=24)
                    result = await session.execute(text(
                        "SELECT COUNT(*) FROM grants WHERE created_at > :cutoff"
                    ), {"cutoff": recent_cutoff})
                    recent_grants = result.scalar()
                    health_info["metrics"]["recent_grants_24h"] = recent_grants
                except SQLAlchemyError:
                    health_info["metrics"]["recent_grants_24h"] = "unknown"
                
                # Overall health assessment
                all_tables_healthy = all(
                    info.get("status") == "healthy" 
                    for info in table_info.values()
                )
                
                if all_tables_healthy and response_time < 5.0:
                    health_info["status"] = "healthy"
                    self.consecutive_failures = 0
                else:
                    health_info["status"] = "degraded"
                    self.consecutive_failures += 1
                    
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_info["status"] = "unhealthy"
            health_info["error"] = str(e)
            self.consecutive_failures += 1
        
        self.last_health_check = datetime.utcnow()
        self.health_status = health_info["status"]
        
        return health_info
    
    async def start_monitoring(self):
        """Start periodic health monitoring."""
        if self.is_monitoring:
            logger.warning("Health monitoring already started")
            return
        
        self.is_monitoring = True
        logger.info(f"Starting database health monitoring (interval: {self.health_check_interval}s)")
        
        while self.is_monitoring:
            try:
                health_result = await self.check_health()
                
                if health_result["status"] == "unhealthy":
                    logger.error(f"Database health check failed: {health_result}")
                    
                    if self.consecutive_failures >= self.max_consecutive_failures:
                        logger.critical(
                            f"Database has failed {self.consecutive_failures} consecutive health checks"
                        )
                        # Could trigger alerts here
                
                elif health_result["status"] == "degraded":
                    logger.warning(f"Database health degraded: {health_result}")
                
                else:
                    logger.debug(f"Database health check passed: {health_result['status']}")
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    def stop_monitoring(self):
        """Stop health monitoring."""
        self.is_monitoring = False
        logger.info("Database health monitoring stopped")
    
    def get_health_status(self) -> str:
        """Get current health status."""
        return self.health_status
    
    def is_healthy(self) -> bool:
        """Check if database is currently healthy."""
        return self.health_status == "healthy"
    
    def needs_recovery(self) -> bool:
        """Check if database needs recovery."""
        return self.consecutive_failures >= self.max_consecutive_failures


class DatabaseRecoveryManager:
    """Manage database recovery operations."""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        self.recovery_in_progress = False
    
    async def attempt_recovery(self) -> bool:
        """Attempt to recover database connectivity."""
        if self.recovery_in_progress:
            logger.warning("Recovery already in progress")
            return False
        
        if self.recovery_attempts >= self.max_recovery_attempts:
            logger.error("Max recovery attempts reached")
            return False
        
        self.recovery_in_progress = True
        self.recovery_attempts += 1
        
        try:
            logger.info(f"Attempting database recovery (attempt {self.recovery_attempts}/{self.max_recovery_attempts})")
            
            # Try to establish a fresh connection
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
                
            logger.info("Database recovery successful")
            self.recovery_attempts = 0
            self.recovery_in_progress = False
            return True
            
        except Exception as e:
            logger.error(f"Database recovery failed: {e}")
            self.recovery_in_progress = False
            return False
    
    def reset_recovery_attempts(self):
        """Reset recovery attempt counter."""
        self.recovery_attempts = 0
        logger.info("Recovery attempts counter reset")


# Global instances
_health_monitor = None
_recovery_manager = None


def get_health_monitor(session_factory) -> DatabaseHealthMonitor:
    """Get or create database health monitor."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = DatabaseHealthMonitor(session_factory)
    return _health_monitor


def get_recovery_manager(session_factory) -> DatabaseRecoveryManager:
    """Get or create database recovery manager."""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = DatabaseRecoveryManager(session_factory)
    return _recovery_manager
