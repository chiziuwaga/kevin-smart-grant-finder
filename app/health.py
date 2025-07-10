"""
Health check and service monitoring utilities.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import services

logger = logging.getLogger(__name__)

class HealthChecker:
    """Comprehensive health checking for all services"""
    
    @staticmethod
    async def check_database() -> Dict[str, Any]:
        """Check database connectivity and health"""
        try:
            if not services.db_sessionmaker:
                return {
                    "status": "unavailable",
                    "message": "Database sessionmaker not initialized",
                    "details": None
                }
            
            async with services.db_sessionmaker() as session:
                # Test basic connectivity
                result = await session.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                
                # Test table existence
                try:
                    await session.execute(text("SELECT COUNT(*) FROM grants"))
                    grants_accessible = True
                except Exception:
                    grants_accessible = False
                
                return {
                    "status": "healthy",
                    "message": "Database connection successful",
                    "details": {
                        "connection_test": test_value == 1,
                        "grants_table_accessible": grants_accessible,
                        "response_time_ms": None  # Could add timing
                    }
                }
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Database error: {str(e)}",
                "details": {"error_type": type(e).__name__}
            }
    
    @staticmethod
    async def check_pinecone() -> Dict[str, Any]:
        """Check Pinecone service health"""
        try:
            if not services.pinecone_client:
                return {
                    "status": "unavailable",
                    "message": "Pinecone client not initialized",
                    "details": None
                }
            
            is_mock = getattr(services.pinecone_client, 'is_mock', False)
            
            if is_mock:
                return {
                    "status": "degraded",
                    "message": "Using mock Pinecone client",
                    "details": {"mock_mode": True}
                }
            
            # Test real Pinecone connection
            connection_ok = services.pinecone_client.verify_connection()
            
            return {
                "status": "healthy" if connection_ok else "unhealthy",
                "message": "Pinecone connection verified" if connection_ok else "Pinecone connection failed",
                "details": {"connection_verified": connection_ok}
            }
            
        except Exception as e:
            logger.error(f"Pinecone health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Pinecone error: {str(e)}",
                "details": {"error_type": type(e).__name__}
            }
    
    @staticmethod
    async def check_perplexity() -> Dict[str, Any]:
        """Check Perplexity service health"""
        try:
            if not services.perplexity_client:
                return {
                    "status": "unavailable",
                    "message": "Perplexity client not initialized",
                    "details": None
                }
            
            is_mock = getattr(services.perplexity_client, 'is_mock', False)
            
            if is_mock:
                return {
                    "status": "degraded",
                    "message": "Using mock Perplexity client",
                    "details": {"mock_mode": True}
                }
            
            # Test with a simple query
            rate_limit = services.perplexity_client.get_rate_limit_status()
            
            return {
                "status": "healthy",
                "message": "Perplexity client operational",
                "details": {
                    "rate_limit_remaining": rate_limit,
                    "mock_mode": False
                }
            }
            
        except Exception as e:
            logger.error(f"Perplexity health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Perplexity error: {str(e)}",
                "details": {"error_type": type(e).__name__}
            }
    
    @staticmethod
    async def check_notifications() -> Dict[str, Any]:
        """Check notification service health"""
        try:
            if not services.notifier:
                return {
                    "status": "unavailable",
                    "message": "Notification manager not initialized",
                    "details": None
                }
            
            is_mock = getattr(services.notifier, 'is_mock', False)
            
            return {
                "status": "degraded" if is_mock else "healthy",
                "message": "Using mock notification manager" if is_mock else "Notification manager operational",
                "details": {"mock_mode": is_mock}
            }
            
        except Exception as e:
            logger.error(f"Notification health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Notification error: {str(e)}",
                "details": {"error_type": type(e).__name__}
            }
    
    @staticmethod
    async def comprehensive_health_check() -> Dict[str, Any]:
        """Perform comprehensive health check of all services"""
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": await HealthChecker.check_database(),
                "pinecone": await HealthChecker.check_pinecone(),
                "perplexity": await HealthChecker.check_perplexity(),
                "notifications": await HealthChecker.check_notifications()
            }
        }
        
        # Determine overall system health
        service_statuses = [service["status"] for service in health_data["services"].values()]
        
        if all(status == "healthy" for status in service_statuses):
            overall_status = "healthy"
        elif any(status == "unhealthy" for status in service_statuses):
            overall_status = "unhealthy"
        elif any(status == "degraded" for status in service_statuses):
            overall_status = "degraded"
        else:
            overall_status = "unknown"
        
        health_data["overall_status"] = overall_status
        health_data["uptime_seconds"] = (
            datetime.utcnow().timestamp() - services.start_time
        ) if services.start_time else None
        
        return health_data
