"""
Main application with graceful degradation and robust error handling.
This is the new entrypoint that integrates all the fixes.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import fixes
from fixes.database.robust_connection_manager import get_connection_manager, get_robust_db_session
from fixes.services.graceful_services import initialize_services, get_service_manager
from fixes.services.circuit_breaker import get_circuit_manager, CIRCUIT_BREAKER_CONFIGS
from fixes.error_handling.global_handlers import (
    enhanced_global_exception_handler,
    enhanced_http_exception_handler,
    enhanced_validation_exception_handler,
    create_error_response
)
from fixes.error_handling.recovery_strategies import get_recovery_manager
from fixes.monitoring.health_endpoints import health_router

# Import original modules
from config.settings import get_settings
from config.logging_config import setup_logging
from app.router import api_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced lifespan manager with graceful service initialization."""
    logger.info("=== Kevin Smart Grant Finder Starting ===")
    startup_start = datetime.utcnow()
    
    try:
        # Initialize settings
        settings = get_settings()
        logger.info(f"Environment: {settings.environment}")
        
        # Initialize database with robust connection management
        logger.info("Initializing robust database connection...")
        connection_manager = await get_connection_manager()
        db_success = connection_manager.is_initialized
        
        if db_success:
            logger.info("✅ Database: Robust connection established")
        else:
            logger.error("❌ Database: Failed to establish connection")
            # Don't fail startup - let the app run with degraded functionality
        
        # Initialize services with graceful degradation
        logger.info("Initializing services with graceful degradation...")
        service_results = await initialize_services(settings)
        
        # Log service initialization results
        successful_services = [k for k, v in service_results.items() if v]
        failed_services = [k for k, v in service_results.items() if not v]
        
        logger.info(f"✅ Services initialized: {successful_services}")
        if failed_services:
            logger.warning(f"⚠️  Services using fallback: {failed_services}")
        
        # Initialize circuit breakers
        circuit_manager = get_circuit_manager()
        for service_name, config in CIRCUIT_BREAKER_CONFIGS.items():
            circuit_manager.get_circuit_breaker(service_name, config)
        
        logger.info("✅ Circuit breakers initialized")
        
        # Initialize recovery manager
        recovery_manager = get_recovery_manager()
        logger.info("✅ Recovery manager initialized")
        
        # Log startup summary
        startup_duration = (datetime.utcnow() - startup_start).total_seconds()
        logger.info(f"=== Startup Complete in {startup_duration:.2f}s ===")
        
        # Show service status
        service_manager = await get_service_manager()
        health_summary = await service_manager.get_health_summary()
        
        logger.info("Service Status Summary:")
        logger.info(f"  Total services: {health_summary['total_services']}")
        logger.info(f"  Healthy: {health_summary['healthy']}")
        logger.info(f"  Degraded: {health_summary['degraded']}")
        logger.info(f"  Failed: {health_summary['failed']}")
        logger.info(f"  Fallback: {health_summary['fallback']}")
        logger.info(f"  Health ratio: {health_summary['health_ratio']:.2%}")
        
        # Application is ready
        logger.info("🚀 Application is ready to serve requests")
        
        yield
        
    except Exception as e:
        logger.error(f"Critical startup error: {e}", exc_info=True)
        logger.error("Application may have limited functionality")
        # Don't raise - allow app to start with degraded functionality
        yield
    
    finally:
        # Cleanup during shutdown
        logger.info("=== Application Shutdown ===")
        try:
            service_manager = await get_service_manager()
            await service_manager.cleanup_services()
            logger.info("✅ Services cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info("=== Shutdown Complete ===")


# Create FastAPI app with graceful degradation
app = FastAPI(
    title="Kevin Smart Grant Finder",
    description="AI-powered grant search and analysis system with graceful degradation",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

def get_allowed_origins():
    """Get allowed origins from environment"""
    import os
    
    # Default allowed origins
    origins = [
        "http://localhost:3000",  # React dev server
        "http://localhost:8080",  # Alternative dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]
    
    # Add production origins from environment
    production_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
    origins.extend([origin.strip() for origin in production_origins if origin.strip()])
    
    return origins

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Length",
        "X-Total-Count",
        "X-Rate-Limit-Remaining",
        "X-Health-Check",
        "X-Graceful-Degradation"
    ],
    max_age=600
)

# Request monitoring middleware
@app.middleware("http")
async def error_monitoring_middleware(request: Request, call_next):
    """Middleware for error monitoring and recovery."""
    start_time = datetime.utcnow()
    request_id = f"req_{int(start_time.timestamp())}"
    
    # Add request ID to context
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        
        # Add headers for monitoring
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = str((datetime.utcnow() - start_time).total_seconds())
        response.headers["X-Graceful-Degradation"] = "enabled"
        
        return response
        
    except Exception as e:
        # Let global exception handler deal with it
        logger.error(f"Request {request_id} failed: {e}")
        raise

# Enhanced global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with recovery."""
    return await enhanced_global_exception_handler(request, exc)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler."""
    return await enhanced_http_exception_handler(request, exc)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Enhanced validation exception handler."""
    return await enhanced_validation_exception_handler(request, exc)

# Health check endpoints
app.include_router(health_router)

# API routes
app.include_router(api_router, prefix="/api")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service status."""
    try:
        service_manager = await get_service_manager()
        health_summary = await service_manager.get_health_summary()
        
        return {
            "message": "Kevin Smart Grant Finder API",
            "version": "2.0.0",
            "status": "operational",
            "features": [
                "graceful_degradation",
                "circuit_breakers",
                "error_recovery",
                "health_monitoring"
            ],
            "services": {
                "total": health_summary["total_services"],
                "healthy": health_summary["healthy"],
                "health_ratio": health_summary["health_ratio"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Root endpoint error: {e}")
        return {
            "message": "Kevin Smart Grant Finder API",
            "version": "2.0.0",
            "status": "degraded",
            "error": "Service status unavailable",
            "timestamp": datetime.utcnow().isoformat()
        }

# System info endpoint
@app.get("/api/system/info")
async def system_info():
    """System information endpoint."""
    try:
        service_manager = await get_service_manager()
        circuit_manager = get_circuit_manager()
        recovery_manager = get_recovery_manager()
        
        return {
            "application": {
                "name": "Kevin Smart Grant Finder",
                "version": "2.0.0",
                "environment": get_settings().environment,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            },
            "services": await service_manager.get_health_summary(),
            "circuit_breakers": circuit_manager.get_health_summary(),
            "recovery": recovery_manager.get_recovery_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"System info error: {e}")
        return create_error_response(
            message="System information unavailable",
            error_code="system_info_error",
            details={"error": str(e)}
        )

# Error test endpoint (for testing error handling)
@app.get("/api/test/error")
async def test_error():
    """Test endpoint for error handling."""
    raise HTTPException(status_code=500, detail="Test error for debugging")

@app.get("/api/test/validation-error")
async def test_validation_error():
    """Test endpoint for validation error handling."""
    raise RequestValidationError(errors=[{
        "loc": ["query", "test_field"],
        "msg": "field required",
        "type": "value_error.missing"
    }])

if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "app_graceful:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
