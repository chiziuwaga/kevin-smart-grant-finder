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
    async def check_pgvector() -> Dict[str, Any]:
        """Check pgvector service health"""
        try:
            if not services.vector_client:
                return {
                    "status": "unavailable",
                    "message": "pgvector client not initialized",
                    "details": None
                }

            is_mock = getattr(services.vector_client, 'is_mock', False)

            if is_mock:
                return {
                    "status": "degraded",
                    "message": "Using mock pgvector client",
                    "details": {"mock_mode": True}
                }

            connection_ok = await services.vector_client.verify_connection()

            return {
                "status": "healthy" if connection_ok else "unhealthy",
                "message": "pgvector connection verified" if connection_ok else "pgvector connection failed",
                "details": {"connection_verified": connection_ok}
            }

        except Exception as e:
            logger.error(f"pgvector health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"pgvector error: {str(e)}",
                "details": {"error_type": type(e).__name__}
            }
    
    @staticmethod
    async def check_deepseek() -> Dict[str, Any]:
        """Check DeepSeek AI service health"""
        try:
            if not services.deepseek_client:
                return {
                    "status": "unavailable",
                    "message": "DeepSeek client not initialized",
                    "details": None
                }

            # Test basic client availability
            has_api_key = bool(services.deepseek_client.api_key)

            return {
                "status": "healthy" if has_api_key else "degraded",
                "message": "DeepSeek client operational" if has_api_key else "DeepSeek client missing API key",
                "details": {
                    "api_key_configured": has_api_key
                }
            }

        except Exception as e:
            logger.error(f"DeepSeek health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"DeepSeek error: {str(e)}",
                "details": {"error_type": type(e).__name__}
            }
    
    @staticmethod
    async def check_notifications() -> Dict[str, Any]:
        """Check email notification service health (Resend)"""
        try:
            if not services.notifier:
                return {
                    "status": "unavailable",
                    "message": "Email notification service not initialized",
                    "details": None
                }

            is_mock = getattr(services.notifier, 'is_mock', False)

            return {
                "status": "degraded" if is_mock else "healthy",
                "message": "Using fallback email notifications" if is_mock else "Resend email service operational",
                "details": {"mock_mode": is_mock}
            }

        except Exception as e:
            logger.error(f"Email notification health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Email notification error: {str(e)}",
                "details": {"error_type": type(e).__name__}
            }
    
    @staticmethod
    async def comprehensive_health_check() -> Dict[str, Any]:
        """Perform comprehensive health check of all services"""
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": await HealthChecker.check_database(),
                "pgvector": await HealthChecker.check_pgvector(),
                "deepseek": await HealthChecker.check_deepseek(),
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
