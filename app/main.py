from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.router import api_router
from app.services import init_services, services
import logging
from config.logging_config import setup_logging
from datetime import datetime
import os
from typing import List
import os
from typing import List
import time
from fastapi.responses import JSONResponse
from sqlalchemy.future import select
from sqlalchemy import text

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def get_allowed_origins() -> List[str]:
    """Get allowed origins from environment or use defaults"""
    env_origins = os.getenv('ALLOWED_ORIGINS')
    if env_origins:
        return env_origins.split(',')
    
    # Default origins for different environments
    if os.getenv('ENVIRONMENT') == 'production':
        return [
            'https://smartgrantfinder.vercel.app',
            'https://www.smartgrantfinder.vercel.app'
        ]
    elif os.getenv('ENVIRONMENT') == 'staging':
        return [
            'https://staging.smartgrantfinder.vercel.app',
            'http://localhost:3000'
        ]
    else:
        # Development - allow localhost and production frontend for testing
        return [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:8000',
            'https://smartgrantfinder.vercel.app'
        ]

# Create FastAPI app
app = FastAPI(
    title="Kevin Smart Grant Finder",
    description="AI-powered grant search and analysis system",
    version="1.0.0",
    docs_url="/api/docs",  # Scoped to /api path
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Enhanced CORS middleware - allow all origins for production debugging
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now to fix CORS issues
    allow_credentials=False,  # Cannot use credentials with allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Length",
        "X-Total-Count",
        "X-Rate-Limit-Remaining"
    ],
    max_age=600
)

# Initialize services on startup
@app.on_event("startup")
async def startup_event():
    """Initialize services and verify connections on startup"""
    logger.info("Starting service initialization steps...")
    try:
        logger.info("Initializing core services via init_services()...")
        await init_services()
        logger.info("init_services() completed successfully")
        
        # Verify database connectivity using services
        if services.db_sessionmaker:
            async with services.db_sessionmaker() as session:
                await session.execute(text("SELECT 1"))
            logger.info("Database connection verified via services")
        else:
            logger.warning("Database sessionmaker not initialized in services")
            
    except Exception as e:
        logger.error(f"Service initialization failed: {e}", exc_info=True)

    logger.info("Service initialization steps completed")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("Shutting down application...")
    try:
        if services.db_engine:
            await services.db_engine.dispose()
            logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)

# Add routes
app.include_router(api_router, prefix="/api")

# Enhanced health check
@app.get("/health")
async def health_check():
    """Enhanced health check endpoint that checks all critical service statuses"""
    try:
        from datetime import datetime
        from app.services import services
        
        health_status = {
            "status": "initializing", 
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "services": {},
            "uptime": time.time() - (services.start_time or time.time()) if services.start_time else 0
        }
    except Exception as import_error:
        logger.error(f"Health check import error: {import_error}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": f"Import error: {str(import_error)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )    
    try:
        logger.info("Starting detailed health check...")
        
        # Check database
        if services.db_sessionmaker:
            try:
                logger.info("Testing database connection...")
                async with services.db_sessionmaker() as session:
                    await session.execute(text("SELECT 1"))
                health_status["services"]["database"] = "healthy"
                logger.info("Database health check passed")
            except Exception as e:
                logger.error(f"Database health check failed: {str(e)}", exc_info=True)
                health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
        else:
            logger.warning("Database sessionmaker not available")
            health_status["services"]["database"] = {"status": "unhealthy", "error": "No database sessionmaker"}

        # Check Perplexity Client
        if services.perplexity_client:
            try:
                logger.info("Testing Perplexity client...")
                rate_limit = services.perplexity_client.get_rate_limit_status()
                health_status["services"]["perplexity"] = {
                    "status": "healthy",
                    "rate_limit_remaining": rate_limit
                }
                logger.info("Perplexity health check passed")
            except Exception as e:
                logger.error(f"Perplexity client check failed: {str(e)}", exc_info=True)
                health_status["services"]["perplexity"] = {"status": "unhealthy", "error": str(e)}
        else:
            logger.warning("Perplexity client not available")
            health_status["services"]["perplexity"] = {"status": "unhealthy", "error": "No Perplexity client"}        
        # Check Pinecone
        if services.pinecone_client:
            try:
                logger.info("Testing Pinecone connection...")
                # Use the verify_connection method
                is_connected = await services.pinecone_client.verify_connection()
                if is_connected:
                    health_status["services"]["pinecone"] = {
                        "status": "healthy",
                        "connection": "verified"
                    }
                    logger.info("Pinecone health check passed")
                else:
                    health_status["services"]["pinecone"] = {
                        "status": "unhealthy",
                        "error": "Connection verification failed"
                    }
                    logger.warning("Pinecone connection verification failed")
            except Exception as e:
                logger.error(f"Pinecone check failed: {str(e)}", exc_info=True)
                health_status["services"]["pinecone"] = {"status": "unhealthy", "error": str(e)}
        else:
            logger.warning("Pinecone client not available")
            health_status["services"]["pinecone"] = {"status": "unhealthy", "error": "No Pinecone client"}
        # Determine overall status
        logger.info("Determining overall health status...")
        service_statuses = [
            s.get("status", s) if isinstance(s, dict) else s 
            for s in health_status["services"].values()
        ]
        
        healthy_count = sum(1 for s in service_statuses if s == "healthy")
        total_count = len(service_statuses)
        
        health_status["status"] = (
            "healthy" if all(s == "healthy" for s in service_statuses)
            else "degraded" if any(s == "healthy" for s in service_statuses)
            else "unhealthy"
        )
        
        health_status["health_summary"] = f"{healthy_count}/{total_count} services healthy"
        
        logger.info(f"Health check completed: {health_status['status']} ({health_status['health_summary']})")

        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(
            status_code=status_code,
            content=health_status
        )

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )