from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.router import api_router
from app.services import init_services
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
            'https://grant-finder.vercel.app',
            'https://www.grant-finder.vercel.app'
        ]
    elif os.getenv('ENVIRONMENT') == 'staging':
        return [
            'https://staging.grant-finder.vercel.app',
            'http://localhost:3000'
        ]
    else:
        # Development - allow localhost
        return [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:8000'
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

# Enhanced CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-Total-Count"
    ],
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
    try:
        logger.info("Initializing services...")
        await init_services()
        
        # Verify database connection
        from database.session import engine
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        logger.info("Database connection verified")
        
        # Verify Pinecone connection
        from utils.pinecone_client import PineconeClient
        pinecone_client = PineconeClient()
        await pinecone_client.verify_connection()
        logger.info("Pinecone connection verified")
        
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}", exc_info=True)
        # Don't raise here - let the app start but in degraded mode

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("Shutting down application...")
    try:
        from database.session import engine
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)

# Add routes
app.include_router(api_router, prefix="/api")

# Enhanced health check
@app.get("/health")
async def health_check():
    """Enhanced health check endpoint that checks all critical service statuses"""
    from datetime import datetime
    from app.services import services
    
    health_status = {
        "status": "initializing",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {},
        "uptime": time.time() - services.get("start_time", time.time())
    }
    
    try:
        # Check database
        if services.get("db_sessionmaker"):
            try:
                async with services["db_sessionmaker"]() as session:
                    await session.execute(text("SELECT 1"))
                health_status["services"]["database"] = "healthy"
            except Exception as e:
                logger.error(f"Database health check failed: {str(e)}", exc_info=True)
                health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}

        # Check Perplexity Client
        if services.get("perplexity_client"):
            try:
                rate_limit = services["perplexity_client"].get_rate_limit_status()
                health_status["services"]["perplexity"] = {
                    "status": "healthy",
                    "rate_limit_remaining": rate_limit
                }
            except Exception as e:
                logger.error(f"Perplexity client check failed: {str(e)}", exc_info=True)
                health_status["services"]["perplexity"] = {"status": "unhealthy", "error": str(e)}

        # Check Pinecone
        if services.get("pinecone_client"):
            try:
                # Basic connectivity check
                stats = services["pinecone_client"].describe_index_stats()
                health_status["services"]["pinecone"] = {
                    "status": "healthy",
                    "total_vector_count": stats.get("total_vector_count", 0)
                }
            except Exception as e:
                logger.error(f"Pinecone check failed: {str(e)}", exc_info=True)
                health_status["services"]["pinecone"] = {"status": "unhealthy", "error": str(e)}

        # Determine overall status
        service_statuses = [
            s.get("status", s) if isinstance(s, dict) else s 
            for s in health_status["services"].values()
        ]
        health_status["status"] = (
            "healthy" if all(s == "healthy" for s in service_statuses)
            else "degraded" if any(s == "healthy" for s in service_statuses)
            else "unhealthy"
        )

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