"""
Health monitoring endpoints for graceful degradation system.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from fixes.database.health_monitor import get_health_monitor, get_recovery_manager
from fixes.services.circuit_breaker import get_circuit_manager
from fixes.error_handling.recovery_strategies import get_recovery_manager as get_error_recovery_manager
from fixes.services.graceful_services import get_service_manager

logger = logging.getLogger(__name__)

# Create router for health endpoints
health_router = APIRouter(prefix="/health", tags=["Health Monitoring"])


@health_router.get("/")
async def basic_health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Service is operational"
    }


@health_router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with all service statuses."""
    health_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "unknown",
        "services": {},
        "metrics": {},
        "errors": []
    }
    
    try:
        # Get service manager
        service_manager = await get_service_manager()
        
        # Check service statuses
        service_statuses = await service_manager.get_service_statuses()
        health_data["services"] = service_statuses
        
        # Check circuit breaker status
        circuit_manager = get_circuit_manager()
        circuit_health = circuit_manager.get_health_summary()
        health_data["circuit_breakers"] = circuit_health
        
        # Check recovery manager stats
        recovery_manager = get_error_recovery_manager()
        recovery_stats = recovery_manager.get_recovery_stats()
        health_data["recovery_stats"] = recovery_stats
        
        # Determine overall health
        healthy_services = sum(1 for status in service_statuses.values() if status.get("status") == "healthy")
        total_services = len(service_statuses)
        
        if healthy_services == total_services:
            health_data["status"] = "healthy"
        elif healthy_services > 0:
            health_data["status"] = "degraded"
        else:
            health_data["status"] = "unhealthy"
        
        # Add metrics
        health_data["metrics"] = {
            "healthy_services": healthy_services,
            "total_services": total_services,
            "health_ratio": healthy_services / total_services if total_services > 0 else 0.0,
            "circuit_breaker_health": circuit_health["health_ratio"],
            "recovery_rate": recovery_stats["recovery_rate"]
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health_data["status"] = "error"
        health_data["errors"].append(str(e))
    
    return health_data


@health_router.get("/database")
async def database_health_check():
    """Database-specific health check."""
    try:
        service_manager = await get_service_manager()
        db_sessionmaker = service_manager.get_service("database")
        
        if not db_sessionmaker:
            return {
                "status": "unavailable",
                "message": "Database service not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Get health monitor
        health_monitor = get_health_monitor(db_sessionmaker)
        health_result = await health_monitor.check_health()
        
        return health_result
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@health_router.get("/services")
async def services_health_check():
    """Check health of all external services."""
    try:
        service_manager = await get_service_manager()
        service_statuses = await service_manager.get_service_statuses()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "services": service_statuses,
            "summary": {
                "total": len(service_statuses),
                "healthy": sum(1 for s in service_statuses.values() if s.get("status") == "healthy"),
                "degraded": sum(1 for s in service_statuses.values() if s.get("status") == "degraded"),
                "unhealthy": sum(1 for s in service_statuses.values() if s.get("status") == "unhealthy")
            }
        }
        
    except Exception as e:
        logger.error(f"Services health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@health_router.get("/circuit-breakers")
async def circuit_breakers_health_check():
    """Check health of all circuit breakers."""
    try:
        circuit_manager = get_circuit_manager()
        circuit_health = circuit_manager.get_health_summary()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            **circuit_health
        }
        
    except Exception as e:
        logger.error(f"Circuit breakers health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@health_router.get("/recovery-stats")
async def recovery_stats_check():
    """Check recovery statistics."""
    try:
        recovery_manager = get_error_recovery_manager()
        recovery_stats = recovery_manager.get_recovery_stats()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            **recovery_stats
        }
        
    except Exception as e:
        logger.error(f"Recovery stats check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@health_router.post("/reset-circuit-breakers")
async def reset_circuit_breakers():
    """Reset all circuit breakers."""
    try:
        circuit_manager = get_circuit_manager()
        circuit_manager.reset_all()
        
        return {
            "status": "success",
            "message": "All circuit breakers reset",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Circuit breaker reset failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@health_router.post("/services/restart")
async def restart_services():
    """Restart all services."""
    try:
        service_manager = await get_service_manager()
        restart_results = await service_manager.restart_services()
        
        return {
            "status": "success",
            "message": "Services restart initiated",
            "results": restart_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Service restart failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@health_router.get("/readiness")
async def readiness_check():
    """Kubernetes-style readiness check."""
    try:
        service_manager = await get_service_manager()
        
        # Check if critical services are available
        critical_services = ["database"]  # Add other critical services as needed
        
        for service_name in critical_services:
            service = service_manager.get_service(service_name)
            if not service:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "not_ready",
                        "message": f"Critical service {service_name} not available",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@health_router.get("/liveness")
async def liveness_check():
    """Kubernetes-style liveness check."""
    try:
        # Basic liveness check - just ensure the application is running
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_alive",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@health_router.get("/startup")
async def startup_check():
    """Check if application has completed startup."""
    try:
        service_manager = await get_service_manager()
        initialization_complete = service_manager.is_initialized()
        
        if not initialization_complete:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "starting",
                    "message": "Application is still starting up",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        return {
            "status": "started",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "startup_failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@health_router.get("/metrics")
async def health_metrics():
    """Get health metrics for monitoring systems."""
    try:
        service_manager = await get_service_manager()
        circuit_manager = get_circuit_manager()
        recovery_manager = get_error_recovery_manager()
        
        # Get service statuses
        service_statuses = await service_manager.get_service_statuses()
        
        # Calculate metrics
        total_services = len(service_statuses)
        healthy_services = sum(1 for s in service_statuses.values() if s.get("status") == "healthy")
        degraded_services = sum(1 for s in service_statuses.values() if s.get("status") == "degraded")
        unhealthy_services = sum(1 for s in service_statuses.values() if s.get("status") == "unhealthy")
        
        # Get circuit breaker metrics
        circuit_health = circuit_manager.get_health_summary()
        
        # Get recovery metrics
        recovery_stats = recovery_manager.get_recovery_stats()
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "service_metrics": {
                "total_services": total_services,
                "healthy_services": healthy_services,
                "degraded_services": degraded_services,
                "unhealthy_services": unhealthy_services,
                "health_ratio": healthy_services / total_services if total_services > 0 else 0.0
            },
            "circuit_breaker_metrics": {
                "total_circuit_breakers": circuit_health["total_circuit_breakers"],
                "open_circuit_breakers": circuit_health["open"],
                "half_open_circuit_breakers": circuit_health["half_open"],
                "closed_circuit_breakers": circuit_health["closed"],
                "circuit_breaker_health_ratio": circuit_health["health_ratio"]
            },
            "recovery_metrics": {
                "total_errors": recovery_stats["total_errors"],
                "recovered_errors": recovery_stats["recovered_errors"],
                "failed_recoveries": recovery_stats["failed_recoveries"],
                "recovery_rate": recovery_stats["recovery_rate"]
            }
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Health metrics failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Health check middleware
async def health_check_middleware(request: Request, call_next):
    """Middleware to add health check headers."""
    response = await call_next(request)
    
    # Add health check headers
    response.headers["X-Health-Check"] = "enabled"
    response.headers["X-Graceful-Degradation"] = "enabled"
    
    return response
